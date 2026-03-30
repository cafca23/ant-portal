import streamlit as st
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import warnings

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

st.title("📊 앤트리치 3대 심리 & 매크로 현황판")
st.write("투자의 나침반! 현재 시장의 분위기를 한눈에 파악하고 매매 타이밍을 잡으세요.")
st.divider()

# ==========================================
# [상단] 3대 지표 (VIX, CNN, KOSPI)
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

    with st.expander("📌 VIX 지수 해석 가이드"):
        st.markdown("""
        - **15 미만 (극도의 탐욕 & 매도)** : 하락 우려 없이 대중이 상승에 취해있는 상태
        - **15 ~ 20 (탐욕 & 매도)** : 경제가 안정적이며 주가가 꾸준히 우상향하는 구간
        - **20 ~ 25 (중립 & 중립)** : 금리, 전쟁 등 악재 뉴스로 변동성이 커지는 구간
        - **25 ~ 40 (공포 & 매수)** : 지수 하락이 눈에 띄며 시장에 공포 심리가 확산
        """)

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

    with st.expander("📌 CNN 지수 해석 가이드"):
        st.markdown("""
        - **0 ~ 25 (극도의 공포 & 매수)** : 대중의 강력한 투매가 일어나는 최고의 매수 기회
        - **25 ~ 45 (공포 & 매수)** : 투자자들이 몸을 사리며 현금을 관망하는 구간
        - **45 ~ 55 (중립 & 중립)** : 수급과 심리가 균형을 이룬 평온한 시장
        - **55 ~ 75 (안정 & 매도)** : 수익 소문이 돌며 대중의 매수세가 몰리는 구간
        """)

# 3. 한국 코스피(KOSPI) 지수 (오류 없는 대체재)
with col3:
    try:
        kospi = yf.Ticker("^KS11")
        kospi_hist = kospi.history(period="5d")['Close']
        kospi_value = float(kospi_hist.iloc[-1])
        kospi_prev = float(kospi_hist.iloc[-2])
        kospi_diff = kospi_value - kospi_prev
        kospi_pct = (kospi_diff / kospi_prev) * 100
        
        if kospi_pct >= 1.5:
            kospi_state = "🟢 강력한 상승 (과열 주의)"
        elif kospi_pct >= 0.5:
            kospi_state = "🟡 상승장 (안정)"
        elif kospi_pct > -0.5:
            kospi_state = "⚪ 횡보장 (눈치 보기)"
        elif kospi_pct > -1.5:
            kospi_state = "🟠 하락장 (경계)"
        else:
            kospi_state = "🔴 급락장 (공포 심리)"
            
        st.metric(label="🇰🇷 한국 코스피 (KOSPI)", value=f"{kospi_value:,.2f}", 
                  delta=f"{kospi_diff:,.2f} ({kospi_pct:+.2f}%)")
        st.markdown(f"**현재 상태: {kospi_state}**")
        telegram_data['KOSPI'] = f"{kospi_value:,.2f} ({kospi_pct:+.2f}%) | {kospi_state}"
        
    except Exception as e:
        st.metric(label="🇰🇷 한국 코스피", value="불러오기 실패")
        telegram_data['KOSPI'] = "데이터 수집 실패"

    with st.expander("📌 KOSPI 지수 해석 가이드"):
        st.markdown("""
        - 한국 증시 전체의 방향성을 보여주는 대표 지수입니다.
        - 미국 지수(VIX, CNN)와 비교하여 국내 시장의 상대적 강세/약세를 파악하세요.
        """)

st.divider()

# ==========================================
# [하단] 거시경제 (Macro)
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
        msg += f"🇰🇷 한국 코스피 : {telegram_data.get('KOSPI', '데이터 없음')}\n\n"
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
