import streamlit as st
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import warnings
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

st.set_page_config(page_title="앤트리치 시황판", page_icon="📊", layout="wide")

# 💡 텔레그램 전송용 함수
def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    return requests.post(url, data=payload)

telegram_data = {}

# ==========================================
# [상단] 타이틀 및 오늘 날짜
# ==========================================
# 요일 한글 변환
days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
now = datetime.now()
today_str = f"{now.year}년 {now.month:02d}월 {now.day:02d}일 {days[now.weekday()]}"

st.title("📊 앤트리치 3대 심리 & 매크로 현황판")
st.markdown(f"<h3 style='color: #38bdf8; margin-top: -10px;'>📅 오늘 날짜: {today_str}</h3>", unsafe_allow_html=True)
st.write("투자의 나침반! 현재 시장의 분위기(심리)가 실제 주가 차트의 어느 위치에 있는지 직관적으로 파악하세요.")
st.divider()

# ==========================================
# [중단 1] 3대 지표 (VIX, CNN, KOSPI 이격도)
# ==========================================
col1, col2, col3 = st.columns(3)

# 1. 미국 VIX 지수
with col1:
    try:
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d")['Close']
        vix_price = float(vix_hist.iloc[-1])
        vix_prev = float(vix_hist.iloc[-2])
        vix_diff = vix_price - vix_prev
        vix_pct = (vix_diff / vix_prev) * 100
        
        if vix_price < 15:
            vix_state = "🟢 극도의 탐욕 & 매도"
        elif vix_price < 20:
            vix_state = "🟡 탐욕 & 매도"
        elif vix_price < 25:
            vix_state = "⚪ 중립 & 중립"
        elif vix_price < 40:
            vix_state = "🟠 공포 & 매수"
        else:
            vix_state = "🔴 극도의 공포 & 매수"
            
        st.metric(label="🇺🇸 미국 VIX (공포 지수)", value=f"{vix_price:.2f}", 
                  delta=f"{vix_diff:.2f} ({vix_pct:.2f}%)", delta_color="inverse")
        st.markdown(f"**현재 상태: {vix_state}**")
        telegram_data['VIX'] = f"{vix_price:.2f} ({vix_pct:+.2f}%) | {vix_state}"
        
    except Exception as e:
        st.metric(label="🇺🇸 미국 VIX", value="불러오기 실패")
        telegram_data['VIX'] = "데이터 수집 실패"

# 2. 미국 CNN 공포/탐욕 지수
with col2:
    try:
        url_cnn = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        res_cnn = requests.get(url_cnn, headers=headers)
        data_cnn = res_cnn.json()
        
        score_cnn = float(data_cnn['fear_and_greed']['score'])
        prev_cnn = float(data_cnn['fear_and_greed']['previous_close'])
        cnn_diff = score_cnn - prev_cnn
        
        if score_cnn <= 25:
            cnn_state = "🔴 극도의 공포 & 매수"
        elif score_cnn <= 45:
            cnn_state = "🟠 공포 & 매수"
        elif score_cnn <= 55:
            cnn_state = "⚪ 중립 & 중립"
        elif score_cnn <= 75:
            cnn_state = "🟡 안정 & 매도"
        else:
            cnn_state = "🟢 극도의 탐욕 & 매도"
            
        st.metric(label="🦅 미국 CNN 지수", value=f"{score_cnn:.1f}", delta=f"{cnn_diff:.1f}")
        st.markdown(f"**현재 상태: {cnn_state}**")
        telegram_data['CNN'] = f"{score_cnn:.1f} ({cnn_diff:+.1f}) | {cnn_state}"
        
    except Exception as e:
        st.metric(label="🦅 미국 CNN 지수", value="불러오기 실패")
        telegram_data['CNN'] = "데이터 수집 실패"

# 3. 한국 KOSPI 이격도 심리 지수
with col3:
    try:
        kospi = yf.Ticker("^KS11")
        ks_hist = kospi.history(period="1mo")['Close']
        
        kospi_value = float(ks_hist.iloc[-1])
        kospi_prev = float(ks_hist.iloc[-2])
        kospi_diff = kospi_value - kospi_prev
        kospi_pct = (kospi_diff / kospi_prev) * 100
        
        ma20 = ks_hist.tail(20).mean()
        disparity = (kospi_value / ma20) * 100
        
        if disparity >= 105:
            ks_state = "🟢 극도의 탐욕 (단기 과열)"
        elif disparity >= 102:
            ks_state = "🟡 탐욕 & 안정 (강세장)"
        elif disparity >= 98:
            ks_state = "⚪ 중립 & 관망 (보합세)"
        elif disparity >= 95:
            ks_state = "🟠 공포 & 줍줍 (단기 침체)"
        else:
            ks_state = "🔴 극도의 공포 (투매/바닥)"
            
        sign = "+" if kospi_diff > 0 else ""
        st.metric(label="🐯 한국 KOSPI (단기 과열/침체 지수)", value=f"{kospi_value:,.2f}", 
                  delta=f"{sign}{kospi_diff:.2f} ({sign}{kospi_pct:.2f}%)")
        st.markdown(f"**시장 심리: {ks_state}**")
        telegram_data['KOSPI'] = f"{kospi_value:,.2f} ({sign}{kospi_pct:.2f}%) | {ks_state}"
        
    except Exception as e:
        st.metric(label="🐯 한국 KOSPI 심리 지수", value="불러오기 실패")
        telegram_data['KOSPI'] = "데이터 수집 실패"

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 📈 [중단 2] 미장 벤치마크 지수 차트 (심리-차트 비교용)
# ==========================================
st.markdown("### 📈 미국 핵심 지수 현재 위치 (심리 지표와 비교용)")
st.markdown("위의 **CNN 공포/탐욕 지수**가 실제 주가 차트의 어느 위치(고점/저점)에서 발생하고 있는지 직관적으로 확인하세요.")

try:
    sp500_hist = yf.Ticker("^GSPC").history(period="1y")
    nasdaq_hist = yf.Ticker("^IXIC").history(period="1y")
    
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
        fig_sp = go.Figure()
        fig_sp.add_trace(go.Scatter(x=sp500_hist.index, y=sp500_hist['Close'], mode='lines', name='S&P 500', line=dict(color='#00b0ff', width=2)))
        
        # 현재 가격 강조 (빨간 점)
        current_sp = sp500_hist['Close'].iloc[-1]
        fig_sp.add_trace(go.Scatter(x=[sp500_hist.index[-1]], y=[current_sp], mode='markers+text', text=[f"{current_sp:,.2f}"], textposition="top left", marker=dict(color='#f85149', size=12), showlegend=False))
        
        fig_sp.update_layout(title="S&P 500 지수 (최근 1년)", template="plotly_dark", height=350, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_sp, use_container_width=True)

    with c_chart2:
        fig_nd = go.Figure()
        fig_nd.add_trace(go.Scatter(x=nasdaq_hist.index, y=nasdaq_hist['Close'], mode='lines', name='NASDAQ', line=dict(color='#e879f9', width=2)))
        
        # 현재 가격 강조 (빨간 점)
        current_nd = nasdaq_hist['Close'].iloc[-1]
        fig_nd.add_trace(go.Scatter(x=[nasdaq_hist.index[-1]], y=[current_nd], mode='markers+text', text=[f"{current_nd:,.2f}"], textposition="top left", marker=dict(color='#f85149', size=12), showlegend=False))
        
        fig_nd.update_layout(title="나스닥 종합지수 (최근 1년)", template="plotly_dark", height=350, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_nd, use_container_width=True)
except Exception as e:
    st.error("차트 데이터를 불러오는 중 오류가 발생했습니다.")

st.divider()

# ==========================================
# [하단 1] 거시경제 (Macro)
# ==========================================
st.header("🌍 거시경제 (Macro) 핵심 지표")
col4, col5 = st.columns(2)

# 4. 환율
with col4:
    try:
        usd_krw = yf.Ticker("KRW=X")
        ex_hist = usd_krw.history(period="5d")['Close']
        ex_price = float(ex_hist.iloc[-1])
        ex_prev = float(ex_hist.iloc[-2])
        ex_diff = ex_price - ex_prev
        ex_pct = (ex_diff / ex_prev) * 100
        
        st.metric(label="💵 달러/원 환율 (USD/KRW)", value=f"{ex_price:,.2f} 원", delta=f"{ex_diff:,.2f} 원 ({ex_pct:.2f}%)")
        telegram_data['환율'] = f"{ex_price:,.2f} 원 ({ex_pct:+.2f}%)"
    except:
        st.metric(label="💵 달러/원 환율", value="불러오기 실패")

# 5. 미국 10년물 국채 금리
with col5:
    try:
        tnx = yf.Ticker("^TNX")
        tnx_hist = tnx.history(period="5d")['Close']
        tnx_price = float(tnx_hist.iloc[-1])
        tnx_prev = float(tnx_hist.iloc[-2])
        tnx_diff = tnx_price - tnx_prev
        tnx_pct = (tnx_diff / tnx_prev) * 100
        
        st.metric(label="🏛️ 미국 10년물 국채 금리", value=f"{tnx_price:.3f} %", delta=f"{tnx_diff:.3f} %p ({tnx_pct:.2f}%)")
        telegram_data['국채금리'] = f"{tnx_price:.3f}% ({tnx_pct:+.2f}%)"
    except:
        st.metric(label="🏛️ 미국 10년물 국채 금리", value="불러오기 실패")

# ==========================================
# [하단 2] 원자재 & 대체 자산
# ==========================================
st.header("🛢️ 원자재 & 대체 자산 (인플레이션 및 유동성)")
col6, col7, col8 = st.columns(3)

with col6:
    try:
        wti = yf.Ticker("CL=F")
        wti_price = float(wti.history(period="5d")['Close'].iloc[-1])
        wti_prev = float(wti.history(period="5d")['Close'].iloc[-2])
        st.metric(label="🛢️ WTI 국제 유가", value=f"$ {wti_price:.2f}", delta=f"{wti_price - wti_prev:.2f} ({(wti_price - wti_prev) / wti_prev * 100:.2f}%)")
        telegram_data['WTI'] = f"${wti_price:.2f}"
    except:
        st.metric(label="🛢️ WTI 국제 유가", value="불러오기 실패")

with col7:
    try:
        gold = yf.Ticker("GC=F")
        gold_price = float(gold.history(period="5d")['Close'].iloc[-1])
        gold_prev = float(gold.history(period="5d")['Close'].iloc[-2])
        st.metric(label="🥇 국제 금값 (Gold)", value=f"$ {gold_price:,.1f}", delta=f"{gold_price - gold_prev:,.1f} ({(gold_price - gold_prev) / gold_prev * 100:.2f}%)")
        telegram_data['금'] = f"${gold_price:,.1f}"
    except:
        st.metric(label="🥇 국제 금값", value="불러오기 실패")

with col8:
    try:
        btc = yf.Ticker("BTC-USD")
        btc_price = float(btc.history(period="5d")['Close'].iloc[-1])
        btc_prev = float(btc.history(period="5d")['Close'].iloc[-2])
        st.metric(label="🪙 비트코인 (BTC)", value=f"$ {btc_price:,.0f}", delta=f"{btc_price - btc_prev:,.0f} ({(btc_price - btc_prev) / btc_prev * 100:.2f}%)")
        telegram_data['BTC'] = f"${btc_price:,.0f}"
    except:
        st.metric(label="🪙 비트코인", value="불러오기 실패")

st.divider()

# ==========================================
# [최하단] 텔레그램 전송
# ==========================================
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])

with col_btn2:
    st.link_button("🏠 앤트리치 블로그로 돌아가기 👉", "https://blog.naver.com/antrich10", use_container_width=True)
    
    if st.button("📲 앤트리치 텔레그램 채널로 시황 전송하기", type="primary", use_container_width=True):
        
        msg = f"📊 <b>[앤트리치 3대 심리 & Macro 현황판]</b>\n\n"
        msg += f"🇺🇸 미국 VIX : {telegram_data.get('VIX', '데이터 없음')}\n"
        msg += f"🦅 미국 CNN : {telegram_data.get('CNN', '데이터 없음')}\n"
        msg += f"🇰🇷 한국 KOSPI : {telegram_data.get('KOSPI', '데이터 없음')}\n\n"
        msg += f"💵 환율(USD/KRW) : {telegram_data.get('환율', '데이터 없음')}\n"
        msg += f"🏛️ 미 10년물 금리 : {telegram_data.get('국채금리', '데이터 없음')}\n"
        msg += f"🛢️ WTI 유가 : {telegram_data.get('WTI', '데이터 없음')}\n"
        msg += f"🥇 금값 : {telegram_data.get('금', '데이터 없음')}\n"
        msg += f"🪙 비트코인 : {telegram_data.get('BTC', '데이터 없음')}\n\n"
        msg += f"<i>👉 자세한 시황 분석은 <a href='https://blog.naver.com/antrich10'>앤트리치 블로그</a>에서 확인하세요!</i>\n"
        msg += f"🔗 https://blog.naver.com/antrich10"

        with st.spinner("텔레그램 채널로 전송 중입니다..."):
            try:
                bot_token = st.secrets["TELEGRAM_BOT_TOKEN"]
                chat_id = st.secrets["TELEGRAM_CHAT_ID"]
                
                res = send_telegram_message(bot_token, chat_id, msg)
                
                if res.status_code == 200:
                    st.success("✅ 텔레그램 채널로 시황 요약이 성공적으로 전송되었습니다!")
                else:
                    st.error(f"🚨 전송 실패: {res.text}")
            except Exception as e:
                st.error(f"🚨 API 세팅 오류: {e}")
