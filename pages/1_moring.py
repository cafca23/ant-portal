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
st.write("미장(아침)부터 국장(마감)까지! 클릭 한 번으로 사람 냄새 나는 시황 포스팅을 구워냅니다.")
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
        
        # 💡 [핵심] 시황 브리핑용 휴먼 블로거 페르소나 프롬프트
        prompt = f"""
        당신은 AI가 아닙니다. 당신은 주식 커뮤니티에서 활동하며 2026년까지 자산 1억 달성을 목표로 치열하게 시장과 씨름하는 '앤트리치' 블로그의 실제 주인입니다.
        절대 기계나 AI가 쓴 글처럼 보이지 않도록, {briefing_time} 독자들에게 친한 주식 투자 동료가 커피 한 잔 마시며 시황 썰을 풀듯 아주 자연스럽고 맛깔나는 문장으로 포스팅을 작성해 주세요.

        [오늘의 데이터 ({target_market})]
        - 1. 주요 지수 마감: \n{index_data}
        - 2. 시장 주도주(대표주) 주가: \n{major_data}
        - 3. 핫이슈 (네이버/구글 뉴스 종합): \n{news_data}

        [출력 필수 구성]
        1. [블로그 제목]: 검색 유입과 호기심을 동시에 잡는 인간적인 어그로 제목 3가지 추천
        
        2. [본문 시작 (인사말 & 시장 마감 한줄평)]:
           - 기계적인 요약 대신 "밤새 미장 보느라 눈이 뻘겋네요~" 또는 "오늘 국장 정말 스펙타클했습니다" 같이 사람 냄새 나게 시작하세요.
        
        3. [증시 요약 & 특징주 썰 풀기]:
           - 수집된 지수와 주가 데이터는 보기 좋게 나열하되, 증시가 왜 이렇게 마감했는지, 특징주는 왜 올랐는지/떨어졌는지는 기계적인 번호 매기기 대신 친한 동료에게 말하듯 자연스러운 줄글(단락)로 썰을 풀어주세요. (🔴상승, 🔵하락 이모지 활용)
        
        4. [앤트리치 인사이트]: 
           - {insight_focus}에 대해 2026년 경제적 자유를 향해 달려가는 앤트리치 관점에서의 대응 전략(추격매수 조심, 관망 등)을 공감 가도록 적어주세요.
        
        5. [블로그용 해시태그]: 관련된 핵심 키워드 10~15개 (쉼표로 구분)
        
        6. [🛡️ 면책 조항]: (※ 본 포스팅은 정보 제공을 위한 참고용일 뿐, 투자의 최종 판단과 책임은 투자자 본인에게 있습니다.)
        
        7. [🎨 제미나이 복사/붙여넣기용 자동 이미지 명령어]: 맨 마지막에 아래 텍스트를 정확하게 출력할 것.
           "이 글에 관련된 이미지 3장 생성해 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘."

        🚨 [절대 금지어 (AI 냄새 나는 단어들)]
        - "요약하자면", "결론적으로", "이 글에서는", "주의가 필요합니다", "살펴보겠습니다", "기대됩니다" 등 전형적인 AI 문구 절대 사용 금지!
        - 대신 "난리 났네요", "대박입니다", "물리신 분들 힘내시길", "슈팅이 나왔네요", "줍줍" 같은 한국 주식 커뮤니티의 은어를 문맥에 맞게 아주 살짝만 섞어주세요.
        """
        
        try:
            response = model.generate_content(prompt)
            st.success(f"🎉 사람 냄새 풀풀 나는 {target_market} 포스팅 초안과 차트 이미지가 완성되었습니다!")
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
