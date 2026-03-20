import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request

# ==========================================
# 0. 페이지 세팅 및 도우미 함수
# ==========================================
st.set_page_config(page_title="앤트리치 MDD 회복일 계산기", page_icon="🛡️", layout="wide")

def format_days_to_ym(days):
    if pd.isna(days) or days == 0:
        return "0일"
    days = int(days)
    years = days // 365
    months = (days % 365) // 30
    if years > 0 and months > 0:
        return f"{days}일 ({years}년 {months}개월)"
    elif years > 0 and months == 0:
        return f"{days}일 ({years}년)"
    elif years == 0 and months > 0:
        return f"{days}일 ({months}개월)"
    else:
        return f"{days}일"

# 💡 한국 주식 네이버 금융 크롤링 (인코딩 자동 감지)
def get_kr_company_name(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=5).read()
        try:
            html = response.decode('utf-8')
        except UnicodeDecodeError:
            html = response.decode('cp949', errors='ignore')
            
        title_start = html.find('<title>') + 7
        title_end = html.find('</title>')
        if title_start > 6 and title_end > -1:
            title_text = html[title_start:title_end]
            return title_text.split(':')[0].strip()
    except:
        pass
    return code 

st.title("🛡️ 앤트리치 MDD & 퀀트 분할매수 계산기")
st.write("과거 데이터를 분석하여 하락장 평균 회복 기간을 구하고, 잃지 않는 분할 매수 타점을 시각화합니다.")
st.divider()

# ==========================================
# 1. 사이드바 (스마트 시장 선택)
# ==========================================
with st.sidebar:
    st.header("⚙️ 분석 설정")
    market = st.radio("🌍 시장 선택", ["미국 주식 (US)", "한국 주식 (KR)"])
    
    if market == "미국 주식 (US)":
        search_input = st.text_input("종목 코드 (예: AAPL, MSFT, TSLA)", value="INTC").upper()
        currency = "$"
    else:
        search_input = st.text_input("종목번호 6자리 (예: 삼성전자 005930)", value="005930")
        currency = "₩"

    target_mdd = st.number_input("목표 분석 하락률 (%)", min_value=-90.0, max_value=-5.0, value=-50.0, step=5.0)
    buffer = st.slider("하락률 오차 범위 (±%)", min_value=1.0, max_value=10.0, value=5.0, step=1.0)
    st.info(f"💡 해석: 과거 역사적 고점 대비 **{target_mdd - buffer}% ~ {target_mdd + buffer}%** 사이로 하락했던 구간들의 회복일만 쏙 뽑아서 평균을 냅니다.")

# ==========================================
# 2. 데이터 수집 및 MDD 알고리즘
# ==========================================
if search_input:
    with st.spinner(f"'{search_input}' 데이터 분석 중... 🕵️‍♂️"):
        
        actual_ticker = search_input
        if market == "한국 주식 (KR)":
            actual_ticker = f"{search_input}.KS"
            data = yf.download(actual_ticker, period="max", progress=False)
            if data.empty:
                actual_ticker = f"{search_input}.KQ"
                data = yf.download(actual_ticker, period="max", progress=False)
            company_name = get_kr_company_name(search_input) # 한국은 네이버 한글명
        else:
            data = yf.download(actual_ticker, period="max", progress=False)
            # 💡 [핵심 요청 반영] 미국 주식은 야후 파이낸스 공식 영어 이름을 가져옵니다.
            try:
                ticker_obj = yf.Ticker(actual_ticker)
                company_name = ticker_obj.info.get('longName') or ticker_obj.info.get('shortName') or search_input
            except:
                company_name = search_input
        
        if data.empty:
            st.error("데이터를 불러오지 못했습니다. 종목 코드(번호)를 다시 확인해 주세요.")
        else:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
            df = data[['Close']].copy().dropna()
            df['Peak'] = df['Close'].cummax()
            df['Drawdown'] = (df['Close'] - df['Peak']) / df['Peak']
            
            current_price = df['Close'].iloc[-1]
            current_peak = df['Peak'].iloc[-1]
            current_dd_pct = df['Drawdown'].iloc[-1] * 100
            
            peak_dates = df[df['Drawdown'] == 0].index
            periods = []
            for i in range(len(peak_dates) - 1):
                start_date, end_date = peak_dates[i], peak_dates[i+1]
                subset = df.loc[start_date:end_date]
                duration_days = (end_date - start_date).days
                if duration_days > 0:
                    max_drop = subset['Drawdown'].min() * 100
                    periods.append({'하락 시작일': start_date, '회복 완료일': end_date, '최대 낙폭(%)': round(max_drop, 2), '회복 소요일(일)': duration_days})
            
            last_peak = peak_dates[-1]
            current_duration = (df.index[-1] - last_peak).days
            periods_df = pd.DataFrame(periods)
            overall_max_mdd = periods_df['최대 낙폭(%)'].min() if not periods_df.empty else current_dd_pct
            overall_max_days = periods_df['회복 소요일(일)'].max() if not periods_df.empty else 0

            # ==========================================
            # 3. 메인 대시보드 출력
            # ==========================================
            st.subheader(f"🏢 기업명 : **{company_name}**")
            
            col1, col2, col3, col4 = st.columns(4)
            if currency == "₩":
                col1.metric(label="현재가", value=f"{currency}{int(current_price):,}")
            else:
                col1.metric(label="현재가", value=f"{currency}{current_price:.2f}")
                
            col2.metric(label="전고점 대비 하락률 (MDD)", value=f"{current_dd_pct:.2f}%", delta=f"전고점({last_peak.strftime('%y.%m.%d')}) 이후 {format_days_to_ym(current_duration)}째", delta_color="inverse")
            col3.metric(label="역대 최악의 폭락 (MAX MDD)", value=f"{overall_max_mdd:.2f}%")
            col4.metric(label="역대 최장 회복기간", value=format_days_to_ym(overall_max_days))
            
            st.divider()
            
            # ==========================================
            # 4. 매수 타점 & 메리트 분석
            # ==========================================
            st.subheader("🎯 기계적 분할 매수 타점 & 메리트 분석")
            total_days = len(df)
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("##### 📍 목표 하락률별 진입 단가")
                target_levels = np.arange(-20, -85, -5) 
                target_data = []
                for lvl in target_levels:
                    target_p = current_peak * (1 + (lvl / 100))
                    better_days = len(df[df['Drawdown'] >= (lvl / 100)])
                    pct = (better_days / total_days) * 100
                    if pct >= 75.0:
                        status = "🔥 진입 시작 (도달)" if current_price <= target_p else "🎯 진입 타겟 (대기중)"
                    else:
                        status = "⚠️ 관망 (메리트 부족)" if current_price <= target_p else "⏳ 대기 중"
                    price_str = f"{currency}{int(target_p):,}" if currency == "₩" else f"{currency}{target_p:.2f}"
                    target_data.append({"목표 하락률": f"{lvl}%", "진입 타겟 단가": price_str, "현재 상태": status})
                
                target_df = pd.DataFrame(target_data)
                def highlight_target_row(row):
                    if "진입 타겟" in row['현재 상태'] or "진입 시작" in row['현재 상태']:
                        return ['background-color: #39ff14; color: black; font-weight: bold;'] * len(row)
                    return [''] * len(row)
                st.dataframe(target_df.style.apply(highlight_target_row, axis=1), use_container_width=True, hide_index=True)
                st.info(f"💡 현재 일별 최고점(ATH)은 **{currency}{int(current_peak):,}** 입니다." if currency == "₩" else f"💡 현재 일별 최고점(ATH)은 **{currency}{current_peak:.2f}** 입니다.")

            with c2:
                st.markdown("##### 📊 하락 깊이별 매수 메리트 (퍼센타일)")
                mdd_bins = np.arange(0, -95, -5)
                percentile_data = []
                for mdd_val in mdd_bins:
                    better_days = len(df[df['Drawdown'] >= (mdd_val / 100)])
                    pct = (better_days / total_days) * 100
                    percentile_data.append({"MDD 깊이": f"{mdd_val}%", "매수 메리트 (역사적 하위%)": f"{pct:.1f}%"})
                
                def highlight_pct(val):
                    try:
                        num = float(val.replace('%', ''))
                        if num >= 75.0: return 'background-color: #fca311; color: black; font-weight: bold;'
                        elif num >= 50.0: return 'background-color: #ffecd1; color: black;'
                    except: pass
                    return ''
                st.dataframe(pd.DataFrame(percentile_data).style.map(highlight_pct, subset=['매수 메리트 (역사적 하위%)']), use_container_width=True, hide_index=True)

            # ==========================================
            # 5. AI 코멘터리 및 차트
            # ==========================================
            st.divider()
            st.subheader("🤖 앤트리치 퀀트 AI 리포트")
            diag_msg = f"🚨 **상태 진단:** 역대급 바닥권입니다!" if current_dd_pct < (overall_max_mdd + 2) else f"📉 **상태 진단:** 현재 침체 구간입니다."
            active_signals = [d for d in target_data if "진입 시작" in d['현재 상태']]
            action_msg = f"🔥 **행동 지침:** 매수 구간에 진입했습니다!" if active_signals else f"⏳ **행동 지침:** 타겟 단가를 기다리세요."
            
            lower_bound, upper_bound = target_mdd - buffer, target_mdd + buffer
            if not periods_df.empty:
                target_periods = periods_df[(periods_df['최대 낙폭(%)'] >= lower_bound) & (periods_df['최대 낙폭(%)'] <= upper_bound)]
                if not target_periods.empty:
                    avg_rec = int(target_periods['회복 소요일(일)'].mean())
                    time_msg = f"⏱️ **멘탈 관리:** 본전 회복까지 평균 **{format_days_to_ym(avg_rec)}** 소요됩니다."
                else: time_msg = "⏱️ **멘탈 관리:** 회복 데이터가 없습니다."
            else: time_msg = "⏱️ **멘탈 관리:** 데이터 부족."
            
            st.info(f"{diag_msg}\n\n{action_msg}\n\n{time_msg}")
            st.subheader("📈 최근 5년 주가 흐름 및 전고점")
            st.line_chart(df.tail(252 * 5)[['Close', 'Peak']].rename(columns={'Close': '현재가', 'Peak': '전고점(본전)'}))
