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
# 1. 사이드바 세팅
# ==========================================
with st.sidebar:
    st.header("⚙️ 분석 설정")
    market = st.radio("🌍 시장 선택", ["미국 주식 (US)", "한국 주식 (KR)"])
    if market == "미국 주식 (US)":
        search_input = st.text_input("종목 코드 (예: AAPL, TSLA)", value="INTC").upper()
        currency = "$"
    else:
        search_input = st.text_input("종목번호 6자리 (예: 005930)", value="005930")
        currency = "₩"
    target_mdd = st.number_input("목표 분석 하락률 (%)", min_value=-90.0, max_value=-5.0, value=-50.0, step=5.0)
    buffer = st.slider("하락률 오차 범위 (±%)", min_value=1.0, max_value=10.0, value=5.0, step=1.0)

# ==========================================
# 2. 데이터 수집 (핵심: 메타데이터 활용)
# ==========================================
if search_input:
    with st.spinner("데이터 분석 중..."):
        actual_ticker = search_input
        if market == "한국 주식 (KR)":
            actual_ticker = f"{search_input}.KS"
            # 💡 [보완] 코스피 먼저 시도, 없으면 코스닥
            ticker_data = yf.Ticker(actual_ticker)
            data = ticker_data.history(period="max")
            if data.empty:
                actual_ticker = f"{search_input}.KQ"
                ticker_data = yf.Ticker(actual_ticker)
                data = ticker_data.history(period="max")
            company_name = get_kr_company_name(search_input)
        else:
            ticker_data = yf.Ticker(actual_ticker)
            data = ticker_data.history(period="max")
            # 💡 [필살기] .info 대신 차단 안 되는 'long_name' 메타데이터 직접 추출
            try:
                company_name = ticker_data.get_history_metadata().get('longName', search_input)
            except:
                company_name = search_input

        if data.empty:
            st.error("데이터를 불러오지 못했습니다. 종목 코드를 확인해 주세요.")
        else:
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
                periods.append({'start': start, 'end': end, 'drop': round(max_drop, 2), 'days': (end - start).days})
            
            periods_df = pd.DataFrame(periods)
            max_mdd = periods_df['drop'].min() if not periods_df.empty else curr_dd
            max_days = periods_df['days'].max() if not periods_df.empty else 0

            # ==========================================
            # 3. 화면 출력
            # ==========================================
            st.subheader(f"🏢 기업명 : **{company_name}**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재가", f"{currency}{int(curr_p):,}" if currency == "₩" else f"{currency}{curr_p:.2f}")
            c2.metric("전고점 대비 하락률", f"{curr_dd:.2f}%", delta=f"전고점({peak_dates[-1].strftime('%y.%m.%d')}) 이후 {format_days_to_ym((df.index[-1]-peak_dates[-1]).days)}째", delta_color="inverse")
            c3.metric("역대 최악 폭락", f"{max_mdd:.2f}%")
            c4.metric("역대 최장 회복", format_days_to_ym(max_days))
            
            st.divider()
            
            # 4. 매수 타점
            st.subheader("🎯 기계적 분할 매수 타점")
            t_lvls = np.arange(-20, -85, -5)
            t_rows = []
            for l in t_lvls:
                tp = curr_peak * (1 + (l/100))
                pct = (len(df[df['Drawdown'] >= (l/100)]) / len(df)) * 100
                if pct >= 75.0:
                    status = "🔥 진입 시작" if curr_p <= tp else "🎯 진입 타겟"
                else:
                    status = "⚠️ 관망" if curr_p <= tp else "⏳ 대기 중"
                t_rows.append({"하락률": f"{l}%", "단가": f"{currency}{int(tp):,}" if currency == "₩" else f"{currency}{tp:.2f}", "상태": status})
            
            def style_row(row):
                if "진입" in row['상태']: return ['background-color: #39ff14; color: black; font-weight: bold;'] * len(row)
                return [''] * len(row)
            st.dataframe(pd.DataFrame(t_rows).style.apply(style_row, axis=1), use_container_width=True, hide_index=True)
            
            # 5. 리포트 & 차트
            st.divider()
            st.info(f"🤖 **앤트리치 AI 진단:** 현재 {curr_dd:.2f}% 하락 중입니다. {'역대급 바닥!' if curr_dd < max_mdd + 2 else '신중한 분할 매수가 필요합니다.'}")
            st.subheader("📈 주가 흐름 (5년)")
            st.line_chart(df.tail(252*5)[['Close', 'Peak']].rename(columns={'Close': '현재가', 'Peak': '전고점'}))
