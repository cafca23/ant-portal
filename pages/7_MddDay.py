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
    if pd.isna(days) or days == 0: return "0일"
    days = int(days)
    years, months = days // 365, (days % 365) // 30
    if years > 0: return f"{days}일 ({years}년 {months}개월)" if months > 0 else f"{days}일 ({years}년)"
    return f"{days}일 ({months}개월)" if months > 0 else f"{days}일"

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
        search_input = st.text_input("종목 코드 (예: AAPL, TSLA, ORCL)", value="INTC").upper()
        currency = "$"
    else:
        search_input = st.text_input("종목번호 6자리 (예: 005930)", value="005930")
        currency = "₩"
    target_mdd = st.number_input("목표 분석 하락률 (%)", min_value=-90.0, max_value=-5.0, value=-50.0, step=5.0)
    buffer = st.slider("하락률 오차 범위 (±%)", min_value=1.0, max_value=10.0, value=5.0, step=1.0)

# ==========================================
# 2. 데이터 수집
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
            # 기업명 추출
            if market == "미국 주식 (US)":
                try:
                    meta = ticker_obj.get_history_metadata()
                    company_name = meta.get('longName') or meta.get('shortName') or search_input
                except: company_name = search_input
            else: company_name = get_kr_company_name(search_input)

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
                periods.append({'max_drop': max_drop, 'days': (end - start).days})
            
            periods_df = pd.DataFrame(periods)
            max_mdd = periods_df['max_drop'].min() if not periods_df.empty else curr_dd
            max_days = periods_df['days'].max() if not periods_df.empty else 0

            # ==========================================
            # 3. 메인 대시보드
            # ==========================================
            st.subheader(f"🏢 기업명 : **{company_name}**")
            c1, c2, c3, c4 = st.columns(4)
            p_format = f"{currency}{int(curr_p):,}" if currency == "₩" else f"{currency}{curr_p:.2f}"
            c1.metric("현재가", p_format)
            c2.metric("전고점 대비 하락률", f"{curr_dd:.2f}%", 
                      delta=f"고점 이후 {format_days_to_ym((df.index[-1]-peak_dates[-1]).days)}째", delta_color="inverse")
            c3.metric("역대 최악 MDD", f"{max_mdd:.2f}%")
            c4.metric("역대 최장 회복", format_days_to_ym(max_days))
            st.divider()

            # ==========================================
            # 4. 타점 및 메리트 분석 (복구)
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
                    if pct >= 75.0: status = "🔥 진입 시작" if curr_p <= tp else "🎯 진입 타겟"
                    else: status = "⚠️ 관망" if curr_p <= tp else "⏳ 대기 중"
                    
                    price_str = f"{currency}{int(tp):,}" if currency == "₩" else f"{currency}{tp:.2f}"
                    t_data.append({"목표 하락률": f"{l}%", "진입 단가": price_str, "현재 상태": status})
                
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
            # 5. AI 리포트 복구
            # ==========================================
            st.divider()
            st.subheader("🤖 앤트리치 퀀트 AI 리포트")
            
            # 진단 로직
            diag = f"🚨 **상태 진단:** 최악의 폭락 수준입니다!" if curr_dd < (max_mdd + 2) else f"📉 **상태 진단:** 현재 고점 대비 {curr_dd:.2f}% 하락한 침체기입니다."
            # 지침 로직
            buy_count = len([d for d in t_data if "진입 시작" in d['현재 상태']])
            action = f"🔥 **행동 지침:** {buy_count}개 구간 초록불! 기계적 매수 타이밍입니다." if buy_count > 0 else "⏳ **행동 지침:** 원칙 단가를 기다리며 현금을 보존하세요."
            # 타임라인 로직
            l_b, u_b = target_mdd - buffer, target_mdd + buffer
            target_periods = periods_df[(periods_df['max_drop'] >= l_b) & (periods_df['max_drop'] <= u_b)]
            avg_rec = f"평균 **{format_days_to_ym(int(target_periods['days'].mean()))}**" if not target_periods.empty else "데이터 부족"
            time_msg = f"⏱️ **멘탈 관리:** 이 정도 하락 시 본전 회복까지 {avg_rec} 소요되었습니다."
            
            st.info(f"{diag}\n\n{action}\n\n{time_msg}")

            # 6. 차트
            st.subheader("📈 최근 5년 주가 흐름 및 전고점")
            st.line_chart(df.tail(252*5)[['Close', 'Peak']].rename(columns={'Close': '현재가', 'Peak': '전고점(본전)'}))
