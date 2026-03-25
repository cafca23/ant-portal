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
import time

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# ==========================================
# 0. AI 및 기본 세팅
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

st.set_page_config(page_title="앤트리치 시황 브리핑", page_icon="🌅", layout="wide")
st.title("🌅 앤트리치 시황 브리핑 봇")
st.write("미장(아침)부터 국장(마감)까지! 클릭 한 번으로 핵심만 짚은 깔끔한 보고서 형태의 시황 포스팅을 구워냅니다.")
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

# 💡 [신규 추가] 국장 마감 전용 팩트 데이터 (추후 pykrx로 교체할 부분)
def get_korean_after_market_data():
    co_buy = [
        {"종목명": "삼성전자", "특징": "외인/기관 동시 순매수 1위 (반도체 턴어라운드 기대)"},
        {"종목명": "SK하이닉스", "특징": "HBM 수요 폭발, 기관 대량 매수"},
        {"종목명": "알테오젠", "특징": "바이오주 훈풍 속 기관 5거래일 연속 매수"}
    ]
    after_hours = [
        {"종목명": "우진엔텍", "상승률": "+9.8%", "특징": "원전 관련 정부 정책 기대감"},
        {"종목명": "에코프로머티", "상승률": "+8.5%", "특징": "장 마감 후 대규모 공급계약 공시"}
    ]
    return co_buy, after_hours

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
btn_text = "🌅 미장 모닝 브리핑 굽기" if "미국" in target_market else "🌇 국장 마감 & 내일 전략 굽기"

if st.button(btn_text, use_container_width=True):
    with st.spinner(f"데이터와 뉴스를 싹쓸이하여 {target_market} 브리핑을 작성 중입니다... ☕ (약 15초 소요)"):
        
        index_data = get_index_data(target_market)
        major_data = get_major_stocks_data(target_market)
        news_data = get_market_news(target_market)
        
        # 💡 국장일 경우에만 쌍끌이/시간외 데이터 텍스트 생성
        extra_market_data = ""
        if "한국" in target_market:
            co_buy, after_hours = get_korean_after_market_data()
            co_buy_str = "\n".join([f"  * {item['종목명']} ({item['특징']})" for item in co_buy])
            after_hours_str = "\n".join([f"  * {item['종목명']} : {item['상승률']} ({item['특징']})" for item in after_hours])
            extra_market_data = f"\n- 4. 세력 쌍끌이 매수 특징주: \n{co_buy_str}\n- 5. 시간외 급등 특징주: \n{after_hours_str}"
        
        briefing_time = "아침 출근길" if "미국" in target_market else "오후 퇴근길"
        insight_focus = "오늘 한국 증시에 미칠 영향" if "미국" in target_market else "내일 시장 대비, 낙수효과 섹터 및 향후 주도주 전망"
        
        prompt = f"""
        당신은 기업의 전문 투자 분석가이자 주식 블로그 '앤트리치'의 수석 에디터입니다. 
        오늘 수집된 데이터를 바탕으로, 블로그에 업로드할 '직장 상사에게 보고하는 개조식 형태'의 시황 브리핑을 작성해 주세요.

        [오늘의 데이터 ({target_market})]
        - 1. 주요 지수 마감: \n{index_data}
        - 2. 시장 주도주(대표주) 주가: \n{major_data}
        - 3. 핫이슈 (뉴스 종합): \n{news_data} {extra_market_data}

        [🚨 매우 중요한 작성 규칙 및 양식]
        1. [어투 종결 강제]: 문장의 끝은 무조건 "~함", "~됨", "~했음", "~예상됨", "~필요함" 형식으로 철저하게 끊어지는 명사형 개조식으로만 작성하세요.
        2. [팩트 강조]: 핵심 팩트(수치, 종목명 등)는 반드시 **굵은 글씨**로 처리하세요.
        3. [구조화]: 줄글은 배제하고 기호(-, *)를 적극 활용하세요.

        [출력 필수 구성]
        1. [보고서 제목] : 블로그에 적합한 제목 3가지 추천 (예: [국장 마감] 기관 쌍끌이 특징주 요약 & 내일 장 전략)
        2. [금일 시장 개요] : 시장의 전체 흐름 1~2줄 요약 보고.
        3. [지수 및 특징주 동향] : 왜 올랐는지/떨어졌는지 주요 원인 보고. (한국 증시일 경우 쌍끌이 매수 및 시간외 급등 종목 내용 포함)
        4. [대응 전략 및 인사이트] : {insight_focus}에 대한 전문적인 분석 제안.
        5. [마법의 1인치: D-Day 캘린더] : 오늘 또는 이번 주 주목할 주요 경제 일정 1~2개 보고.
        6. [마법의 1인치: 영상 픽] : 아래 텍스트를 그대로 출력하여 에디터가 요약본을 넣을 자리를 만들어 줄 것.
           "▶️ **[오늘의 핵심 유튜브 요약]** \n (에디터님, 여기에 직접 분석하신 유튜브 3줄 요약을 넣어주세요!)"
        7. [블로그용 해시태그] : 핵심 키워드 10개
        8. [🛡️ 면책 조항] : 투자 책임은 본인에게 있음 명시.
        9. [🎨 이미지 AI용 만화 주문서]: 맨 마지막에 4컷 만화 주문서를 작성해 주세요. 
           - 반드시 포함할 지시사항: "중요: 만화 이미지를 합치지 말고, 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘."
           - 각 컷마다 시장 상황에 맞는 [장면 묘사]와 3040 개미 투자자의 [말풍선 대사] 포함.
        """
        
        try:
            response = model.generate_content(prompt)
            st.success(f"🎉 각 잡힌 {target_market} 보고서 초안이 완성되었습니다!")
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
            st.error("🚨 앗! AI 일일 무료 한도를 초과했습니다. API 키를 교체해 주세요!")
        except Exception as e:
            st.error(f"🚨 알 수 없는 오류가 발생했습니다: {e}")
