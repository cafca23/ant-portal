import streamlit as st
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import warnings
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

st.set_page_config(page_title="앤트리치 시황판", page_icon="📊", layout="wide")

# 텔레그램 전송용 함수
def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    return requests.post(url, data=payload)

telegram_data = {}

# ==========================================
# [상단] 타이틀 및 오늘 날짜
# ==========================================
days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
now = datetime.now()
today_str = f"{now.year}년 {now.month:02d}월 {now.day:02d}일 {days[now.weekday()]}"

st.title("📊 앤트리치 3대 심리 & 매크로 현황판")
st.markdown(f"<h3 style='color: #38bdf8; margin-top: -10px;'>📅 오늘 날짜: {today_str}</h3>", unsafe_allow_html=True)
st.write("심리가 꺾일 때가 기회다! VIX 지수와 주가 차트를 겹쳐서 현재의 정확한 위치를 파악하세요.")
st.divider()

# ==========================================
# [중단 1] 3대 지표 (VIX, CNN, KOSPI 이격도)
# ==========================================
col1, col2, col3 = st.columns(3)

# 1. 미국 VIX 지수
with col1:
    try:
        vix_ticker = yf.Ticker("^VIX")
        vix_hist_data = vix_ticker.history(period="5d")['Close']
        vix_price = float(vix_hist_data.iloc[-1])
        vix_prev = float(vix_hist_data.iloc[-2])
        vix_diff = vix_price - vix_prev
        vix_pct = (vix_diff / vix_prev) * 100
        
        if vix_price < 15: vix_state = "🟢 극도의 탐욕 (매도 신호)"
        elif vix_price < 20: vix_state = "🟡 탐욕 (비중 축소)"
        elif vix_price < 25: vix_state = "⚪ 중립 (관망)"
        elif vix_price < 40: vix_state = "🟠 공포 (분할 매수)"
        else: vix_state = "🔴 극도의 공포 (적극 매수)"
            
        st.metric(label="🇺🇸 미국 VIX (시장 공포심리)", value=f"{vix_price:.2f}", 
                  delta=f"{vix_diff:.2f} ({vix_pct:.2f}%)", delta_color="inverse")
        st.markdown(f"**현재 상태: {vix_state}**")
        telegram_data['VIX'] = f"{vix_price:.2f} ({vix_pct:+.2f}%) | {vix_state}"
    except:
        st.metric(label="🇺🇸 미국 VIX", value="불러오기 실패")

# 2. 미국 CNN 공포/탐욕 지수
with col2:
    try:
        url_cnn = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        res_cnn = requests.get(url_cnn, headers=headers)
        data_cnn = res_cnn.json()
        score_cnn = float(data_cnn['fear_and_greed']['score'])
        prev_cnn = float(data_cnn['fear_and_greed']['previous_close'])
        cnn_diff = score_cnn - prev_cnn
        
        if score_cnn <= 25: cnn_state = "🔴 극도의 공포"
        elif score_cnn <= 45: cnn_state = "🟠 공포"
        elif score_cnn <= 55: cnn_state = "⚪ 중립"
        elif score_cnn <= 75: cnn_state = "🟡 탐욕"
        else: cnn_state = "🟢 극도의 탐욕"
            
        st.metric(label="🦅 미국 CNN 공포/탐욕 지수", value=f"{score_cnn:.1f}", delta=f"{cnn_diff:.1f}")
        st.markdown(f"**현재 상태: {cnn_state}**")
        telegram_data['CNN'] = f"{score_cnn:.1f} ({cnn_diff:+.1f}) | {cnn_state}"
    except:
        st.metric(label="🦅 미국 CNN 지수", value="불러오기 실패")

# 3. 한국 KOSPI 이격도
with col3:
    try:
        kospi = yf.Ticker("^KS11")
        ks_hist = kospi.history(period="1mo")['Close']
        kospi_value = float(ks_hist.iloc[-1])
        ma20 = ks_hist.tail(20).mean()
        disparity = (kospi_value / ma20) * 100
        
        if disparity >= 105: ks_state = "🟢 극도의 탐욕 (과열)"
        elif disparity >= 102: ks_state = "🟡 탐욕 (안정)"
        elif disparity >= 98: ks_state = "⚪ 중립"
        elif disparity >= 95: ks_state = "🟠 공포 (침체)"
        else: ks_state = "🔴 극도의 공포 (바닥)"
            
        st.metric(label="🐯 한국 KOSPI 지수", value=f"{kospi_value:,.2f}", delta=f"이격도 {disparity:.1f}%")
        st.markdown(f"**시장 심리: {ks_state}**")
        telegram_data['KOSPI'] = f"{kospi_value:,.2f} | {ks_state}"
    except:
        st.metric(label="🐯 한국 KOSPI", value="불러오기 실패")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 📈 [중단 2] VIX 오버레이 하이브리드 차트
# ==========================================
st.markdown("### 📈 주가 vs 공포지수(VIX) 상관관계 분석")
st.info("💡 **차트 읽는 법:** 파란색(주가)이 내려가고 오렌지색(VIX)이 치솟을 때가 역사적인 바닥 매수 기회입니다.")

try:
    # 데이터 로드 (1년치)
    vix_data = yf.Ticker("^VIX").history(period="1y")['Close']
    sp500_data = yf.Ticker("^GSPC").history(period="1y")['Close']
    nasdaq_data = yf.Ticker("^IXIC").history(period="1y")['Close']

    # 1. S&P 500 + VIX 차트
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 주가 (왼쪽 축)
    fig1.add_trace(go.Scatter(x=sp500_data.index, y=sp500_data, name="S&P 500", line=dict(color='#00b0ff', width=2)), secondary_y=False)
    # VIX (오른쪽 축)
    fig1.add_trace(go.Scatter(x=vix_data.index, y=vix_data, name="VIX (공포)", line=dict(color='#ffa726', width=1.5, dash='dot'), opacity=0.7), secondary_y=True)
    
    # 현재가 표시
    fig1.add_trace(go.Scatter(x=[sp500_data.index[-1]], y=[sp500_data.iloc[-1]], mode='markers+text', text=[f"{sp500_data.iloc[-1]:,.0f}"], textposition="top center", marker=dict(color='#f85149', size=10), showlegend=False), secondary_y=False)

    fig1.update_layout(title="S&P 500 & VIX 하이브리드 (1Y)", template="plotly_dark", height=400, margin=dict(l=0, r=0, t=40, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig1.update_yaxes(title_text="주가 (USD)", secondary_y=False, showgrid=True, gridcolor='#30363d')
    fig1.update_yaxes(title_text="VIX 지수", secondary_y=True, showgrid=False)
    
    st.plotly_chart(fig1, use_container_width=True)

    # 2. NASDAQ + VIX 차트
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 주가 (왼쪽 축)
    fig2.add_trace(go.Scatter(x=nasdaq_data.index, y=nasdaq_data, name="NASDAQ", line=dict(color='#e879f9', width=2)), secondary_y=False)
    # VIX (오른쪽 축)
    fig2.add_trace(go.Scatter(x=vix_data.index, y=vix_data, name="VIX (공포)", line=dict(color='#ffa726', width=1.5, dash='dot'), opacity=0.7), secondary_y=True)
    
    # 현재가 표시
    fig2.add_trace(go.Scatter(x=[nasdaq_data.index[-1]], y=[nasdaq_data.iloc[-1]], mode='markers+text', text=[f"{nasdaq_data.iloc[-1]:,.0f}"], textposition="top center", marker=dict(color='#f85149', size=10), showlegend=False), secondary_y=False)

    fig2.update_layout(title="나스닥 & VIX 하이브리드 (1Y)", template="plotly_dark", height=400, margin=dict(l=0, r=0, t=40, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig2.update_yaxes(title_text="주가 (USD)", secondary_y=False, showgrid=True, gridcolor='#30363d')
    fig2.update_yaxes(title_text="VIX 지수", secondary_y=True, showgrid=False)
    
    st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"차트 생성 중 오류 발생: {e}")

st.divider()

# ==========================================
# [하단] 거시경제 및 텔레그램 (기존 로직 유지)
# ==========================================
col_m1, col_m2 = st.columns(2)
with col_m1:
    try:
        ex_price = float(yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1])
        st.metric("💵 달러/원 환율", f"{ex_price:,.2f} 원")
        telegram_data['환율'] = f"{ex_price:,.2f}원"
    except: pass
with col_m2:
    try:
        tnx_price = float(yf.Ticker("^TNX").history(period="1d")['Close'].iloc[-1])
        st.metric("🏛️ 미 10년물 국채 금리", f"{tnx_price:.3f} %")
        telegram_data['국채금리'] = f"{tnx_price:.3f}%"
    except: pass

col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    if st.button("📲 텔레그램 채널로 시황 전송하기", type="primary", use_container_width=True):
        msg = f"📊 <b>[{today_str} 시황판]</b>\n\n"
        msg += f"🇺🇸 VIX 공포지수: {telegram_data.get('VIX', '-')}\n"
        msg += f"🦅 CNN Fear&Greed: {telegram_data.get('CNN', '-')}\n\n"
        msg += f"💵 환율: {telegram_data.get('환율', '-')}\n"
        msg += f"🏛️ 국채금리: {telegram_data.get('국채금리', '-')}\n"
        msg += f"\n<i>👉 차트 분석은 앤트리치 포털에서 확인하세요!</i>"
        
        try:
            res = send_telegram_message(st.secrets["TELEGRAM_BOT_TOKEN"], st.secrets["TELEGRAM_CHAT_ID"], msg)
            if res.status_code == 200: st.success("✅ 전송 완료!")
            else: st.error("🚨 전송 실패")
        except: st.error("🚨 API 설정 오류")
