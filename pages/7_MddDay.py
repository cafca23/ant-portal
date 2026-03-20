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

# 💡 한국 주식 네이버 금융 크롤링 (한국 주식용 한글명)
def get_kr_company_name(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=5).read()
        try:
            html = response.decode('utf-8')
        except:
            html = response.decode('cp949', errors='ignore')
            
        title_start = html.find('<title>') + 7
        title_end = html.find('</title>')
        if title_start > 6 and title_end > -1:
            return html[title_start:title_end].split(':')[0].strip()
    except:
        pass
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
        search_input = st.text_input("종목 코드 (예: AAPL, MSFT, TSLA)", value="INTC").upper()
        currency = "$"
    else:
        search_input = st.text_input("종목번호 6자리 (예: 005930)", value="005930")
        currency = "₩"

    target_mdd = st.number_input("목표 분석 하락률 (%)", min_value=-90.0, max_value=-5.0, value=-50.0, step=5.0)
    buffer = st.slider("하락률 오차 범위 (±%)", min_value=1.0, max_value=10.0, value=5.0, step=1.0)

# ==========================================
# 2. 데이터 수집 및 기업명 추출 (차단 방지 로직)
# ==========================================
if search_input:
    with st.spinner(f"'{search_input}' 데이터 분석 중..."):
        actual_ticker = search_input
        
        # yfinance Ticker 객체 생성
        ticker_obj = yf.Ticker(actual_ticker if market == "미국 주식 (US)" else f"{search_input}.KS")
        
        # 데이터 다운로드 (최대 기간)
        data = ticker_obj.history(period="max")
        
        # 한국 주식 코스닥 재시도 로직
        if market == "한국 주식 (KR)" and data.empty:
            actual_ticker = f"{search_input}.KQ"
            ticker_obj = yf.Ticker(actual_ticker)
            data = ticker_obj.history(period="max")

        if data.empty:
            st.error("데이터를 불러오지 못했습니다. 종목 코드를 확인해 주세요.")
        else:
            # 💡 [핵심] 영어 풀네임 가져오기 (차단 안되는 메타데이터 활용)
            if market == "미국 주식 (US)":
                try:
                    # 메타데이터에서 longName 추출, 없으면 shortName이나 티커 사용
                    meta = ticker_obj.get_history_metadata()
                    company_name = meta.get('longName') or meta.get('shortName') or search_input
                except:
                    company_name = search_input
            else:
                company_name = get_kr_company_name(search_input)

            # 데이터 가공
            df = data[['Close']].copy().dropna()
            df['Peak'] = df['Close'].cummax()
            df['Drawdown'] = (df['Close'] - df['Peak']) / df['Peak']
            
            current_price = df['Close'].iloc[-1]
            current_peak = df['Peak'].iloc[-1]
            current_dd_pct = df['Drawdown'].iloc[-1] * 100
            
            peak_dates = df[df['Drawdown'] == 0].index
            last_peak = peak_dates[-1]
            current_duration = (df.index[-1] - last_peak).days

            # MDD 구간 계산
            periods = []
            for i in range(len(peak_dates) - 1):
                start_date, end_date = peak_dates[i], peak_dates[i+1]
                subset = df.loc[start_date:end_date]
                duration_days = (end_date - start_date).days
                if duration_days > 0:
                    max_drop = subset['Drawdown'].min() * 100
                    periods.append({'max_drop': max_drop, 'days': duration_days})
            
            periods_df = pd.DataFrame(periods)
            overall_max_mdd = periods_df['max_drop'].min() if not periods_df.empty else current_dd_pct
            overall_max_days = periods_df['days'].max() if not periods_df.empty else 0

            # ==========================================
            # 3. 메인 대시보드 출력
            # ==========================================
            st.subheader(f"🏢 기업명 : **{company_name}**")
            
            col1, col2, col3, col4 = st.columns(4)
            p_format = f"{currency}{int(current_price):,}" if currency == "₩" else f"{currency}{current_price:.2f}"
            col1.metric(label="현재가", value=p_format)
            col2.metric(label="MDD (전고점 대비)", value=f"{current_dd_pct:.2f}%", 
                       delta=f"{format_days_to_ym(current_duration)}째 하락중", delta_color="inverse")
            col3.metric(label="역대 최악 MDD", value=f"{overall_max_mdd:.2f}%")
            col4.metric(label="역대 최장 회복기간", value=format_days_to_ym(overall_max_days))
            
            st.divider()

            # 4. 매수 타점 분석
            st.subheader("🎯 기계적 분할 매수 타점")
            c1, c2 = st.columns([1, 1])
            with c1:
                target_levels = np.arange(-20, -85, -5)
                target_data = []
                for lvl in target_levels:
                    tp = current_peak * (1 + (lvl / 100))
                    pct = (len(df[df['Drawdown'] >= (lvl / 100)]) / len(df)) * 100
                    status = "🔥 진입 시작" if current_price <= tp and pct >= 75 else ("🎯 진입 타겟" if pct >= 75 else "⏳ 대기")
                    target_data.append({"목표 하락률": f"{lvl}%", "타겟 단가": f"{currency}{tp:,.2f}" if currency == "$" else f"{currency}{int(tp):,}", "상태": status})
                
                st.dataframe(pd.DataFrame(target_data), use_container_width=True, hide_index=True)

            with c2:
                st.markdown("##### 📈 주가 흐름 (최근 5년)")
                st.line_chart(df.tail(252 * 5)[['Close', 'Peak']].rename(columns={'Close': '현재가', 'Peak': '전고점'}))
