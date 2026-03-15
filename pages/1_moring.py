import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import matplotlib.pyplot as plt
import urllib.request
import urllib.parse
import json
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# ==========================================
# 0. AI 및 위장 신분증 기본 세팅
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

st.set_page_config(page_title="앤트리치 모닝 브리핑", page_icon="🌅")
st.title("🌅 앤트리치 모닝 브리핑 봇")
st.write("버튼 한 번으로 간밤의 글로벌 시황 텍스트와 블로그용 차트 이미지를 동시에 뽑아냅니다.")
st.divider()

# ==========================================
# 1. 데이터 수집 함수들
# ==========================================
def get_index_data():
    indices = {"다우존스": "^DJI", "S&P 500": "^GSPC", "나스닥": "^IXIC", "필라델피아 반도체": "^SOX"}
    results = []
    for name, ticker in indices.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")
            price = float(data['Close'].iloc[-1])
            prev_price = float(data['Close'].iloc[-2])
            pct_change = ((price - prev_price) / prev_price) * 100
            results.append(f"- {name}: {price:,.2f} ({pct_change:+.2f}%)")
        except:
            results.append(f"- {name}: 불러오기 실패")
    return "\n".join(results)

def get_m7_data():
    m7_tickers = {"엔비디아": "NVDA", "테슬라": "TSLA", "애플": "AAPL", "마이크로소프트": "MSFT", "알파벳(구글)": "GOOGL", "아마존": "AMZN", "메타": "META"}
    results = []
    for name, ticker in m7_tickers.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")
            price = float(data['Close'].iloc[-1])
            prev_price = float(data['Close'].iloc[-2])
            pct_change = ((price - prev_price) / prev_price) * 100
            results.append(f"- {name}: ${price:.2f} ({pct_change:+.2f}%)")
        except:
            results.append(f"- {name}: 불러오기 실패")
    return "\n".join(results)

# 💡 [핵심 업그레이드] 네이버 + 구글 듀얼 엔진으로 아침 뉴스 긁어오기
def get_morning_news():
    news_results = []
    
    # [엔진 1] 네이버 뉴스 (국내 언론의 미장 해석 및 국장 전망)
    try:
        client_id = st.secrets["NAVER_CLIENT_ID"]
        client_secret = st.secrets["NAVER_CLIENT_SECRET"]
        query = urllib.parse.quote("뉴욕증시 마감 OR 미 증시 특징주 OR 글로벌 증시")
        url_naver = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5&sort=sim"
        
        request = urllib.request.Request(url_naver)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)
        
        response_naver = urllib.request.urlopen(request)
        if response_naver.getcode() == 200:
            data = json.loads(response_naver.read().decode('utf-8'))
            for item in data['items']:
                clean_title = BeautifulSoup(item['title'], 'html.parser').text
                news_results.append(f"[네이버 속보] {clean_title}")
    except Exception as e:
        pass

    # [엔진 2] 구글 뉴스 (글로벌 원문 팩트 위주)
    try:
        url_google = "https://news.google.com/rss/search?q=뉴욕 증시 마감 OR 미국 증시 특징주 when:1d&hl=ko&gl=KR&ceid=KR:ko"
        res_google = requests.get(url_google, headers=headers)
        soup_google = BeautifulSoup(res_google.text, "html.parser")
        for news in soup_google.find_all("item")[:5]:
            news_results.append(f"[구글 뉴스] {news.title.text}")
    except:
        pass
        
    if not news_results:
        return "- 뉴스 데이터 불러오기 실패"
    return "\n".join(news_results)

# 블로그용 차트 이미지 생성기
def create_chart_image(ticker, title_name):
    try:
        data = yf.Ticker(ticker).history(period="1mo")
        fig, ax = plt.subplots(figsize=(7, 4))
        
        line_color = 'red' if data['Close'].iloc[-1] >= data['Close'].iloc[0] else 'blue'
        
        ax.plot(data.index, data['Close'], color=line_color, linewidth=2)
        ax.set_title(f"{title_name} Trend (1 Month)", fontsize=14, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.6)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        return fig
    except:
        return None

# ==========================================
# 2. 메인 실행 버튼
# ==========================================
if st.button("🌅 오늘 아침 글로벌 시황 포스팅 굽기", use_container_width=True):
    with st.spinner("간밤의 미장 데이터와 듀얼 엔진 뉴스를 싹쓸이하여 브리핑을 작성 중입니다... ☕ (약 15초 소요)"):
        
        # 1단계: 텍스트 재료 가져오기
        index_data = get_index_data()
        m7_data = get_m7_data()
        news_data = get_morning_news()
        
        # 2단계: 텍스트 생성용 AI 프롬프트 (네이버 속보 반영 지시 추가)
        prompt = f"""
        당신은 '앤트리치(Antrich)' 주식 블로그의 전문 시황 분석가입니다.
        다음 수집된 아침 데이터를 바탕으로, 독자들이 출근길에 1분 만에 읽고 시장을 파악할 수 있는 [모닝 브리핑] 블로그 포스팅 초안을 작성해 주세요.

        [오늘의 데이터]
        - 1. 글로벌 지수 마감:
        {index_data}
        - 2. M7 빅테크 주가:
        {m7_data}
        - 3. 간밤의 핫이슈 (네이버/구글 뉴스 종합):
        {news_data}

        [포스팅 필수 구성 및 순서]
        1. ☀️ 아침 인사 & 간밤의 미장 한줄평
        2. 📊 뉴욕 증시 마감 브리핑 (🔴빨간색, 🔵파란색 이모지 활용)
        3. 🍎 M7 빅테크 특징주 요약
        4. 📰 오늘의 관전 포인트 & 앤트리치 인사이트 (특히 수집된 뉴스를 바탕으로 오늘 한국 증시에 미칠 영향을 한 줄 꼭 포함하세요!)
        5. 🏷️ 오늘의 핫 키워드 태그 (검색 유입용)
            - 오늘 시황과 제공된 뉴스에서 사람들이 가장 많이 검색할 만한 핵심 키워드(특징 종목명, 테마, 경제 이슈 등)를 뽑아서 네이버 블로그용 해시태그 10~15개를 리스트 형태로 작성해 주세요. (예: #미국증시, #엔비디아, #S&P500 ...)
        6. 🛡️ 면책 조항 (※ 본 포스팅은 정보 제공을 위한 참고용일 뿐, 특정 종목에 대한 매수 및 매도를 추천하는 글이 아닙니다. 투자의 최종 판단과 책임은 투자자 본인에게 있습니다.)

        [작성 규칙]
        - 네이버 블로그에 바로 복사+붙여넣기 할 수 있도록 HTML 태그 없이 깔끔하게 텍스트로만 작성하세요.
        - 친근하면서도 신뢰감을 주는 경어체(~습니다, ~하네요)를 사용하세요.
        """
        
        try:
            response = model.generate_content(prompt)
            st.success("🎉 듀얼 엔진 기반 포스팅 초안과 차트 이미지가 완성되었습니다!")
            st.markdown(response.text)
            
            st.divider()
            
            # 3단계: 블로그용 이미지 출력 구역
            st.subheader("📸 블로그 본문용 차트 이미지")
            st.caption("👇 마우스 우클릭 -> [이미지를 다른 이름으로 저장] 후 블로그에 바로 올리세요!")
            
            col1, col2 = st.columns(2)
            with col1:
                fig1 = create_chart_image("^GSPC", "S&P 500")
                if fig1: st.pyplot(fig1)
            with col2:
                fig2 = create_chart_image("NVDA", "NVIDIA")
                if fig2: st.pyplot(fig2)
                
        except ResourceExhausted:
            st.error("🚨 앗! AI 과부하 상태입니다. 딱 1분만 기다리셨다가 다시 버튼을 눌러주세요!")
        except Exception as e:
            st.error(f"🚨 알 수 없는 오류가 발생했습니다: {e}")
