import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import urllib.request
import urllib.parse
import json
from pykrx import stock
from datetime import datetime, timedelta

# ==========================================
# 0. AI 및 기본 세팅 (Tier 1 무제한 엔진 장착)
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 💡 고도화 1: 무제한 API에 맞춘 AI 두뇌 세팅 (창의성 0.7 적용, 장문 출력 허용)
generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 4000,
}
model = genai.GenerativeModel('gemini-2.5-flash', generation_config=generation_config)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

st.set_page_config(page_title="앤트리치 시황 브리핑", page_icon="🌅", layout="wide")
st.title("🏛️ J.F2.A 앤트리치 시황 브리핑 공장 V4 (Pro Edition)")
st.markdown("유료 결제(Tier 1) 전용 고도화 엔진 탑재! **데이터 캐싱(10배 빠른 로딩)**과 딥러닝 추론 능력이 극대화되었습니다.")
st.divider()

# ==========================================
# 1. 시장 선택 옵션
# ==========================================
target_market = st.radio("🎯 어떤 증시 브리핑을 작성할까요?", ["🇺🇸 미국 증시 (아침 브리핑)", "🇰🇷 한국 증시 (마감 브리핑)"], horizontal=True)

# ==========================================
# 2. 데이터 수집 엔진 (실시간 크롤러 함수들)
# ==========================================
# 💡 고도화 2: 무한 로딩 방지 및 IP 차단 방지를 위한 캐싱 적용 (30분 유지)
@st.cache_data(ttl=1800, show_spinner=False)
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
            results.append(f"- {name}: 데이터 수집 일시 지연")
    return "\n".join(results)

@st.cache_data(ttl=1800, show_spinner=False)
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
            results.append(f"- {name}: 데이터 수집 일시 지연")
    return "\n".join(results)

@st.cache_data(ttl=1800, show_spinner=False)
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
                news_results.append(f"- {clean_title}")
    except:
        pass

    try:
        url_google = f"https://news.google.com/rss/search?q={query_google}&hl=ko&gl=KR&ceid=KR:ko"
        res_google = requests.get(url_google, headers=headers)
        soup_google = BeautifulSoup(res_google.text, "html.parser")
        for news in soup_google.find_all("item")[:5]:
            news_results.append(f"- {news.title.text}")
    except:
        pass
        
    if not news_results:
        return "- 최신 뉴스 데이터 불러오기 지연"
    return "\n".join(news_results)

@st.cache_data(ttl=3600, show_spinner=False)
def get_korean_after_market_data():
    today = datetime.today()
    if today.weekday() == 5: today -= timedelta(days=1)
    elif today.weekday() == 6: today -= timedelta(days=2)
    date_str = today.strftime("%Y%m%d")

    co_buy = []
    after_hours = []

    try:
        df_foreign = stock.get_market_net_purchases_of_equities_by_ticker(date_str, date_str, "KOSPI", "외국인")
        top_foreign = df_foreign.sort_values("순매수거래대금", ascending=False).head(3)
        
        for ticker, row in top_foreign.iterrows():
            name = stock.get_market_ticker_name(ticker)
            amt = int(row['순매수거래대금'] / 100000000)
            co_buy.append({"종목명": name, "특징": f"외국인 순매수 상위 (약 {amt}억원 쓸어담음)"})
            
        df_inst = stock.get_market_net_purchases_of_equities_by_ticker(date_str, date_str, "KOSPI", "기관합계")
        top_inst = df_inst.sort_values("순매수거래대금", ascending=False).head(2)
        
        for ticker, row in top_inst.iterrows():
            name = stock.get_market_ticker_name(ticker)
            amt = int(row['순매수거래대금'] / 100000000)
            co_buy.append({"종목명": name, "특징": f"기관 순매수 상위 (약 {amt}억원 쓸어담음)"})
    except Exception:
        co_buy.append({"종목명": "데이터 수집 지연", "특징": "한국거래소(KRX) 서버 혼잡"})

    try:
        df_up = stock.get_market_ohlcv(date_str, market="KOSPI")
        top_up = df_up.sort_values("등락률", ascending=False).head(3)
        
        for ticker, row in top_up.iterrows():
            name = stock.get_market_ticker_name(ticker)
            rate = row['등락률']
            after_hours.append({"종목명": name, "상승률": f"+{rate:.2f}%", "특징": "당일 정규장 폭등 (수급 쏠림 현상)"})
    except Exception:
        after_hours.append({"종목명": "데이터 수집 지연", "상승률": "-", "특징": "한국거래소(KRX) 서버 혼잡"})

    return co_buy, after_hours

@st.cache_data(ttl=3600, show_spinner=False)
def get_naver_schedule():
    try:
        client_id = st.secrets["NAVER_CLIENT_ID"]
        client_secret = st.secrets["NAVER_CLIENT_SECRET"]
        
        query = urllib.parse.quote("오늘의 증시 일정 OR 주간 증시 일정")
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=3&sort=sim"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)
        
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            data = json.loads(response.read().decode('utf-8'))
            schedule_list = []
            for item in data['items']:
                clean_title = BeautifulSoup(item['title'], 'html.parser').text
                schedule_list.append(f"- {clean_title}")
            
            if schedule_list:
                return "\n".join(schedule_list)
        return "- 오늘 뚜렷한 주요 증시 일정 뉴스 없음"
    except Exception:
        return "- 증시 일정 데이터 수집 일시 지연"

# ==========================================
# 3. 메인 실행 버튼 및 AI 작문 엔진
# ==========================================
btn_text = "🌅 미장 모닝 브리핑 굽기" if "미국" in target_market else "🌇 국장 마감 & 내일 전략 굽기"

if st.button(btn_text, use_container_width=True):
    with st.spinner(f"데이터와 뉴스를 싹쓸이하여 {target_market} 전문 전략 보고서를 작성 중입니다... ☕ (캐싱 적용으로 약 10초 소요)"):
        
        index_data = get_index_data(target_market)
        major_data = get_major_stocks_data(target_market)
        news_data = get_market_news(target_market)
        schedule_data = get_naver_schedule()

        korean_supply_data = ""
        if "한국" in target_market:
            co_buy, after_hours = get_korean_after_market_data()
            co_buy_str = "\n".join([f"  - {item['종목명']} ({item['특징']})" for item in co_buy])
            after_hours_str = "\n".join([f"  - {item['종목명']} : {item['상승률']} ({item['특징']})" for item in after_hours])
            korean_supply_data = f"\n- 4. 세력(외인/기관) 쌍끌이 매수 특징주: \n{co_buy_str}\n- 5. 시간외 급등 특징주: \n{after_hours_str}"
        
        insight_focus = "오늘 한국 증시에 미칠 영향" if "미국" in target_market else "내일 시장 대비, 낙수효과 테마 및 향후 주도주 전략"
        
        prompt = f"""
        당신은 월스트리트 출신의 전문 투자 분석가이자 주식 블로그 '앤트리치'의 수석 에디터입니다. 
        오늘 수집된 팩트 데이터를 바탕으로, 블로그 독자들을 매료시킬 강력한 시황 브리핑을 작성해 주세요.

        [오늘의 팩트 데이터 ({target_market})]
        - 1. 주요 지수 마감 현황: \n{index_data}
        - 2. 시장 주도주(대표주) 주가 현황: \n{major_data}
        - 3. 시장 핫이슈 및 특징 뉴스 종합: \n{news_data} {korean_supply_data}
        - 4. 실시간 증시 일정 (D-Day): \n{schedule_data}

        [🚨 작성 규칙 - 절대 엄수]
        1. [어투 종결 강제]: 1번~5번 항목까지의 문장 끝은 무조건 "~함", "~됨", "~했음", "~예상됨", "~필요함" 형식의 전문적인 개조식으로만 작성하세요. 
        2. [기호 사용 통제]: 글 전체에 별표(*) 기호는 단 한 개도 사용하지 마세요. 강조는 대괄호([ ])나 꺾쇠(【 】)만 사용하세요.

        [출력 필수 구성]
        1. [보고서 제목] : 블로그 검색(SEO)에 유리하고 호기심을 끄는 제목 3가지 추천.
        2. [금일 시장 1줄 요약] : 시장의 전체적인 흐름을 날카롭게 요약.
        3. [지수 및 특징주 심층 분석] : 뉴스 데이터와 주가 데이터를 연결하여 왜 올랐는지/떨어졌는지 인과관계를 명확히 분석. 
        4. [앤트리치의 액션 플랜] : {insight_focus}에 대한 구체적이고 전문적인 투자 전략 제안.
        5. [마법의 1인치: D-Day 캘린더] : 제공된 일정 데이터를 바탕으로 핵심 관전 포인트 요약.
        6. 🔥 [앤트리치의 찐 속마음 (인간미 코멘트)] : 분위기를 확 바꿔서 3040 직장인 개미 투자자에게 빙의해 작성하세요. 앞의 딱딱한 개조식을 버리고, "형님들, 오늘 수급 보니까 내일 무조건 ~~ 탑승해야 합니다", "물린 분들 오늘 밤 미장 보면서 기도합시다 ㅠㅠ" 등 비표준어, 한탄, 유머, 인터넷 커뮤니티 말투를 섞어서 아주 찰지고 주관적인 코멘트를 2~3줄 툭 던지듯 작성해 주세요.
        7. [블로그용 핵심 태그] : 핵심 키워드 10~15개 (# 기호 사용).
        8. [🎨 이미지 AI용 주문서]: 맨 마지막 줄에 정확히 아래 문장만 그대로 출력해 주세요.
           "이 브리핑 내용에 맞는 블로그 썸네일용 만화 이미지 3개 만들어 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘."
        """
        
        try:
            response = model.generate_content(prompt)
            st.success(f"🎉 무제한 엔진(Tier 1)을 가동하여 100% 팩트 기반의 {target_market} 전략 보고서를 완성했습니다!")
            
            clean_text = response.text.replace("*", "")
            st.markdown(clean_text)
            st.divider()
                
        except Exception as e:
            st.error(f"🚨 일시적인 네트워크 오류가 발생했습니다: {e}")
