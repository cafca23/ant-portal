import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import json

# ==========================================
# 0. 페이지 세팅 및 도우미 함수
# ==========================================
st.set_page_config(page_title="앤트리치 MDD 회복일 계산기", page_icon="🛡️", layout="wide")

def format_days_to_ym(days):
    if pd.isna(days) or days == 0: return "0일"
    days = int(days)
    years, months = days // 365, (days % 365) // 30
    if years > 0: return f"{days}일 ({years}년 {months}개월)" if months > 0 else f"{days}일 ({years}년)"
    return f"{days}일 ({months}개월)" if months > 0 else f"{days}일"

# 💡 한국 주식 네이버 금융 크롤링 (자동 인코딩 감지)
def get_kr_company_name(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        res = urllib.request.urlopen(req, timeout=5).read()
        try: html = res.decode('utf-8')
        except: html = res.decode('cp949', errors='ignore')
        t_start = html.find('<title>') + 7
        t_end = html.find('</title>')
        if t_start > 6 and t_end > -1: return html[t_start:t_end].split(':')[0].strip()
    except: pass
    return code

# 💡 [필살기] 미국 주식 야후 파이낸스 공식 검색 API 직접 호출 (절대 안 막힘)
def get_us_company_name(ticker):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, headers=headers)
        res = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        data = json.loads(res)
        if 'quotes' in data and len(data['quotes']) > 0:
            # longname(풀네임)을 1순위로 가져오고, 없으면 shortname을 가져옵니다.
            return data['quotes'][0].get('longname') or data['quotes'][0].get('shortname') or ticker
    except: pass
    
    # 만약 API가 실패할 경우 최후의 보루
    try:
        info = yf.Ticker(ticker).info
        return info.get('longName') or info.get('shortName') or ticker
    except: return ticker

st.title("🛡️ 앤트리치 MDD & 퀀트 분할매수 계산기")
st.write("과거 데이터를 분석하여 하락장 평균 회복 기간을 구하고, 잃지 않는 분할 매수 타점을 시각화합니다.")
st.divider()

# ==========================================
# 1. 사이드바 설정
# ==========================================
with st.sidebar:
    st.header("⚙️ 분석 설정")
    market = st.radio("🌍 시장 선택", ["미국 주식 (US)", "한국 주식 (KR)"])
    if market == "미국 주식 (US)":
        search_input = st.text_input("종목 코드 (예: AAPL, TSLA, INTC)", value="INTC").upper()
        currency = "$"
    else:
        search_input = st.text_input("종목번호 6자리 (예: 005930)", value="005930")
        currency = "₩"
    target_mdd = st.number_input("목표 분석 하락률 (%)", min_value=-90.0, max_value=-5.0, value=-30.0, step=5.0)
    buffer = st.slider("하락률 오차 범위 (±%)", min_value=1.0, max_value=10.0, value=5.0, step=1.0)

# ==========================================
# 2. 데이터 수집 및 가공
# ==========================================
if search_input:
    with st.spinner("데이터 분석 중..."):
        actual_ticker = search_input
        ticker_obj = yf.Ticker(actual_ticker if market == "미국 주식 (US)" else f"{search_input}.KS")
        data = ticker_obj.history(period="max")
        
        if market == "한국 주식 (KR)" and data.empty:
            actual_ticker = f"{search_input}.KQ"
            ticker_obj = yf.Ticker(actual_ticker)
            data = ticker_obj.history(period="max")

        if data.empty:
            st.error("데이터를 불러오지 못했습니다. 종목 코드를 확인해 주세요.")
        else:
            # 🏢 기업명 멱살 잡고 가져오기!
            if market == "미국 주식 (US)":
                company_name = get_us_company_name(search_input)
            else:
                company_name = get_kr_company_name(search_input)

            # 데이터 가공
            df = data[['Close']].copy().dropna()
            df['Peak'] = df['Close'].cummax()
            df['Drawdown'] = (df['Close'] - df['Peak']) / df['Peak']
            
            curr_p, curr_peak = df['Close'].iloc[-1], df['Peak'].iloc[-1]
            curr_dd = df['Drawdown'].iloc[-1] * 100
            
            peak_dates = df[df['Drawdown'] == 0].index
            periods = []
            for i in range(len(peak_dates) - 1):
                start, end = peak_dates[i], peak_dates[i+1]
                max_drop = df.loc[start:end, 'Drawdown'].min() * 100
                periods.append({'start': start, 'end': end, 'max_drop': max_drop, 'days': (end - start).days})
            
            periods_df = pd.DataFrame(periods)
            max_mdd_val = periods_df['max_drop'].min() if not periods_df.empty else curr_dd
            max_days_val = periods_df['days'].max() if not periods_df.empty else 0

            # ==========================================
            # 3. 상단 메인 대시보드
            # ==========================================
            st.subheader(f"🏢 기업명 : **{company_name}**")
            c1, c2, c3, c4 = st.columns(4)
            p_format = f"{currency}{int(curr_p):,}" if currency == "₩" else f"{currency}{curr_p:.2f}"
            c1.metric("현재가", p_format)
            c2.metric("전고점 대비 하락률 (MDD)", f"{curr_dd:.2f}%", 
                      delta=f"고점 이후 {format_days_to_ym((df.index[-1]-peak_dates[-1]).days)}째", delta_color="inverse")
            c3.metric("역대 최악의 폭락 (MAX MDD)", f"{max_mdd_val:.2f}%")
            c4.metric("역대 최장 회복기간", format_days_to_ym(max_days_val))
            st.divider()

            # ==========================================
            # 4. 타점 및 메리트 분석 표
            # ==========================================
            st.subheader("🎯 기계적 분할 매수 타점 & 메리트 분석")
            col_a, col_b = st.columns(2)
            total_days = len(df)
            
            with col_a:
                st.markdown("##### 📍 목표 하락률별 진입 단가")
                t_lvls = np.arange(-20, -85, -5)
                t_data = []
                for l in t_lvls:
                    tp = curr_peak * (1 + (l/100))
                    pct = (len(df[df['Drawdown'] >= (l/100)]) / total_days) * 100
                    if pct >= 75.0: status = "🔥 진입 시작 (도달)" if curr_p <= tp else "🎯 진입 타겟 (대기중)"
                    else: status = "⚠️ 관망 (메리트 부족)" if curr_p <= tp else "⏳ 대기 중"
                    
                    price_str = f"{currency}{int(tp):,}" if currency == "₩" else f"{currency}{tp:.2f}"
                    t_data.append({"목표 하락률": f"{l}%", "진입 타겟 단가": price_str, "현재 상태": status})
                
                t_df = pd.DataFrame(t_data)
                def style_row(row):
                    if "진입" in row['현재 상태']: return ['background-color: #39ff14; color: black; font-weight: bold;'] * len(row)
                    return [''] * len(row)
                st.dataframe(t_df.style.apply(style_row, axis=1), use_container_width=True, hide_index=True)

            with col_b:
                st.markdown("##### 📊 하락 깊이별 매수 메리트 (퍼센타일)")
                m_bins = np.arange(0, -95, -5)
                m_data = []
                for m in m_bins:
                    pct = (len(df[df['Drawdown'] >= (m/100)]) / total_days) * 100
                    m_data.append({"MDD 깊이": f"{m}%", "매수 메리트 (역사적 하위%)": f"{pct:.1f}%"})
                
                def highlight_pct(val):
                    try:
                        num = float(val.replace('%', ''))
                        if num >= 75.0: return 'background-color: #fca311; color: black; font-weight: bold;'
                        elif num >= 50.0: return 'background-color: #ffecd1; color: black;'
                    except: pass
                    return ''
                st.dataframe(pd.DataFrame(m_data).style.map(highlight_pct, subset=['매수 메리트 (역사적 하위%)']), use_container_width=True, hide_index=True)

            # ==========================================
            # 5. [수호] 폭락장 평균 회복 기간 분석 섹션
            # ==========================================
            st.divider()
            st.subheader(f"⏱️ [{target_mdd}%] 수준 폭락장 평균 회복 기간")
            l_b, u_b = target_mdd - buffer, target_mdd + buffer
            target_periods = periods_df[(periods_df['max_drop'] >= l_b) & (periods_df['max_drop'] <= u_b)]
            
            rc1, rc2, rc3 = st.columns(3)
            if not target_periods.empty:
                avg_days = int(target_periods['days'].mean())
                max_days_in_range = int(target_periods['days'].max())
                rc1.metric("조건 부합 횟수", f"{len(target_periods)}회")
                rc2.metric("평균 회복일", format_days_to_ym(avg_days))
                rc3.metric("해당 구간 최장 회복일", format_days_to_ym(max_days_in_range))
                st.write(f"💡 **앤트리치 퀀트 전략:** 통계상 **{l_b}% ~ {u_b}%** 사이로 하락했을 때, 전고점 탈환에 평균 **{format_days_to_ym(avg_days)}**이 걸렸습니다. 자금 투입 시 이 기간을 염두에 두고 호흡을 조절하세요!")
            else:
                st.warning(f"역사상 {l_b}% ~ {u_b}% 수준의 하락 후 회복된 기록이 없습니다.")

            # ==========================================
            # 6. AI 리포트 및 차트
            # ==========================================
            st.divider()
            st.subheader("🤖 앤트리치 퀀트 AI 리포트")
            diag_msg = f"🚨 **상태 진단:** 현재 하락률({curr_dd:.2f}%)이 역대 최악의 폭락 수준에 근접하거나 이미 갱신했습니다!" if curr_dd < (max_mdd_val + 2) else f"📉 **상태 진단:** 현재 고점 대비 {curr_dd:.2f}% 하락한 침체기입니다."
            active_buy = len([d for d in t_data if "진입 시작" in d['현재 상태']])
            action_msg = f"🔥 **행동 지침:** 총 {active_buy}개 구간 초록불! 기계적 매수 타이밍입니다." if active_buy > 0 else "⏳ **행동 지침:** 원칙 단가를 기다리며 현금을 보존하세요."
            time_msg = f"⏱️ **멘탈 관리:** 통계상 본전 회복까지 약 {format_days_to_ym(int(target_periods['days'].mean())) if not target_periods.empty else '장기전'}이 소요될 수 있는 구간입니다."
            
            st.info(f"{diag_msg}\n\n{action_msg}\n\n{time_msg}")

            st.subheader("📈 최근 5년 주가 흐름 및 전고점")
            st.line_chart(df.tail(252*5)[['Close', 'Peak']].rename(columns={'Close': '현재가', 'Peak': '전고점(본전)'}))
