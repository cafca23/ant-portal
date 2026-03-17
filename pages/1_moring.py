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

st.set_page_config(page_title="앤트리치 시황 브리핑", page_icon="🌅")
st.title("🌅 앤트리치 시황 브리핑 봇")
st.write("미장(아침)부터 국장(마감)까지! 클릭 한 번으로 완벽한 시황 포스팅을 구워냅니다.")
st.divider()

# ==========================================
# 1. 시장 선택 옵션
# ==========================================
target_market = st.radio("어떤 증시 브리핑을 작성할까요?", ["🇺🇸 미국 증시 (아침 브리핑)", "🇰🇷 한국 증시 (마감 브리핑)"], horizontal=True)

# ==========================================
# 2. 데이터 수집 함수들
# ==========================================
def get_index_data(market_type):
    if "미국" in market_type:
        indices = {"다우존스": "^DJI", "S&P 500": "^GSPC", "나스닥": "^IXIC", "필라델피아 반도체": "^SOX"}
    else:
        indices = {"코스피": "^KS11", "코스닥": "^KQ11", "코스피 200": "^KS200"}
        
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

def get_major_stocks_data(market_type):
    if "미국" in market_type:
        tickers = {"엔비디아": "NVDA", "테슬라": "TSLA", "애플": "AAPL", "마이크로소프트": "MSFT", "알파벳": "GOOGL"}
        currency = "$"
    else:
        tickers = {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS", "LG에너지솔루션": "373220.KS", "KB금융": "105560.KS"}
        currency = "₩"
        
    results = []
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")
            price = float(data['Close'].iloc[-1])
            prev_price = float(data['Close'].iloc[-2])
            pct_change = ((price - prev_price) / prev_price) * 100
            if currency == "₩":
                results.append(f"- {name}: {price:,.0f}원 ({pct_change:+.2f}%)")
            else:
                results.append(f"- {name}: ${price:.2f} ({pct_change:+.2f}%)")
        except:
            results.append(f"- {name}: 불러오기 실패")
    return "\n".join(results)

def get_market_news(market_type):
    news_results = []
    
    if "미국" in market_type:
        query_naver = "뉴욕증시 마감 OR 미 증시 특징주 OR 글로벌 증시"
        query_google = "뉴욕 증시 마감 OR 미국 증시 특징주 when:1d"
    else:
        query_naver = "코스피 마감 OR 코스닥 마감 OR 국내 증시 특징주"
        query_google = "코스피 시황 OR 한국 증시 마감 특징주 when:1d"

    try:
        client_id = st.secrets["NAVER_CLIENT_ID"]
        client_secret = st.secrets["NAVER_CLIENT_SECRET"]
        query = urllib.parse.quote(query_naver)
        url_naver = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5&sort=sim"
        
        request = urllib.request.Request(url_naver)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)
        
        response_naver = urllib.request.urlopen(request)
        if response_naver.getcode() == 200:
            data = json.loads(response_naver.read().decode('utf-8'))
            for item in data['items']:
                clean_title = BeautifulSoup(item['title'], 'html.parser').text
                news_results.append(f"[네이버] {clean_title}")
    except:
        pass

    try:
        url_google = f"https://news.google.com/rss/search?q={query_google}&hl=ko&gl=KR&ceid=KR:ko"
        res_google = requests.get(url_google, headers=headers)
        soup_google = BeautifulSoup(res_google.text, "html.parser")
        for news in soup_google.find_all("item")[:5]:
            news_results.append(f"[구글] {news.title.text}")
    except:
        pass
        
    if not news_results:
        return "- 뉴스 데이터 불러오기 실패"
    return "\n".join(news_results)

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
# 3. 메인 실행 버튼
# ==========================================
btn_text = "🌅 미장 모닝 브리핑 굽기" if "미국" in target_market else "🌇 국장 마감 브리핑 굽기"

if st.button(btn_text, use_container_width=True):
    with st.spinner(f"데이터와 뉴스를 싹쓸이하여 {target_market} 브리핑을 작성 중입니다... ☕ (약 15초 소요)"):
        
        index_data = get_index_data(target_market)
        major_data = get_major_stocks_data(target_market)
        news_data = get_market_news(target_market)
        
        briefing_time = "아침 출근길" if "미국" in target_market else "오후 퇴근길"
        insight_focus = "오늘 한국 증시에 미칠 영향" if "미국" in target_market else "내일 시장 대비 및 향후 주도주 전망"
        
        prompt = f"""
        당신은 '앤트리치(Antrich)' 주식 블로그의 전문 시황 분석가입니다.
        다음 수집된 데이터를 바탕으로, 독자들이 {briefing_time}에 1분 만에 읽고 시장을 파악할 수 있는 블로그 포스팅 초안을 작성해 주세요.

        [오늘의 데이터 ({target_market})]
        - 1. 주요 지수 마감:
        {index_data}
        - 2. 시장 주도주(대표주) 주가:
        {major_data}
        - 3. 핫이슈 (네이버/구글 뉴스 종합):
        {news_data}

        [포스팅 필수 구성 및 순서]
        1. ☀️ 인사말 & 시장 마감 한줄평
        2. 📊 증시 마감 요약 (🔴상승, 🔵하락 이모지 활용)
        3. 🎯 주요 특징주 요약 (왜 올랐는지/떨어졌는지 뉴스 기반으로 설명)
        4. 📰 오늘의 관전 포인트 & 앤트리치 인사이트 ({insight_focus}을 반드시 포함하세요!)
        5. 🏷️ 오늘의 핫 키워드 태그 (검색 유입용)
            - 오늘 시황에서 가장 많이 검색될 핵심 키워드 10~15개를 리스트로 작성 (예: #코스피, #삼성전자, #증시마감 ...)
        6. 🛡️ 면책 조항 (※ 본 포스팅은 정보 제공을 위한 참고용일 뿐, 투자의 최종 판단과 책임은 투자자 본인에게 있습니다.)
        7. 🎨 제미나이 복사/붙여넣기용 자동 이미지 명령어 (가장 마지막 줄에 아래 텍스트를 정확하게 출력할 것)
            "이 글에 관련된 이미지 3장 생성해 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘."

        [작성 규칙]
        - 네이버 블로그에 바로 복사+붙여넣기 할 수 있도록 HTML 태그 없이 깔끔하게 텍스트로만 작성하세요.
        - 친근하면서도 전문성을 주는 경어체(~습니다, ~하네요)를 사용하세요.
        """
        
        try:
            response = model.generate_content(prompt)
            st.success(f"🎉 {target_market} 포스팅 초안과 차트 이미지가 완성되었습니다!")
            st.markdown(response.text)
            
            st.divider()
            
            st.subheader("📸 블로그 본문용 차트 이미지")
            st.caption("👇 마우스 우클릭 -> [이미지를 다른 이름으로 저장] 후 블로그에 바로 올리세요!")
            
            col1, col2 = st.columns(2)
            with col1:
                ticker1 = "^GSPC" if "미국" in target_market else "^KS11"
                title1 = "S&P 500" if "미국" in target_market else "KOSPI"
                fig1 = create_chart_image(ticker1, title1)
                if fig1: st.pyplot(fig1)
            with col2:
                ticker2 = "NVDA" if "미국" in target_market else "005930.KS"
                title2 = "NVIDIA" if "미국" in target_market else "Samsung Elec"
                fig2 = create_chart_image(ticker2, title2)
                if fig2: st.pyplot(fig2)
                
        except ResourceExhausted:
            st.error("🚨 앗! AI 과부하 상태입니다. 딱 1분만 기다리셨다가 다시 버튼을 눌러주세요!")
        except Exception as e:
            st.error(f"🚨 알 수 없는 오류가 발생했습니다: {e}")
