import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import urllib.request
import urllib.parse
import json
import re
from datetime import datetime, timedelta
import warnings # <--- 깔끔하게 기본 모듈 임포트

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# ==========================================
# 0. AI 및 기본 세팅 (Tier 1 무제한 엔진 장착)
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 8000, # 💡 넉넉한 출력량을 위해 토큰 상향
}
model = genai.GenerativeModel('gemini-2.5-flash', generation_config=generation_config)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

st.set_page_config(page_title="앤트리치 시황 브리핑", page_icon="🌅", layout="wide")
st.title("🏛️ J.F2.A 앤트리치 시황 브리핑 공장 V4.2 (Pro Edition)")
st.markdown("유료 결제(Tier 1) 전용 고도화 엔진 탑재! **실시간 검색 랭킹 융합**과 **독자적인 수급 스크래핑 엔진**으로 오류 없이 완벽한 보고서를 출력합니다.")
st.divider()

# ==========================================
# 1. 시장 선택 옵션
# ==========================================
target_market = st.radio("🎯 어떤 증시 브리핑을 작성할까요?", ["🇺🇸 미국 증시 (아침 브리핑)", "🇰🇷 한국 증시 (마감 브리핑)"], horizontal=True)

# ==========================================
# 2. 데이터 수집 엔진 (실시간 크롤러 함수들)
# ==========================================

# 💡 [업그레이드] 네이버 실시간 검색어 랭킹 스크래퍼 추가
@st.cache_data(ttl=60, show_spinner=False)
def get_naver_search_ranks_string():
    url = "https://finance.naver.com/sise/lastsearch2.naver"
    rank_text = ""
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('table', {'class': 'type_5'})
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    rank_tag = cols[0]
                    name_tag = cols[1].find('a', class_='tltle')
                    if name_tag and rank_tag.text.strip().isdigit():
                        rank = int(rank_tag.text.strip())
                        name = name_tag.text.strip()
                        rank_text += f"{rank}위: {name}\n"
    except:
        pass
    return rank_text

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

# 💡 [업그레이드] 에러 덩어리 pykrx를 버리고 네이버 증권을 다이렉트로 스크래핑하는 독자 엔진 탑재
@st.cache_data(ttl=1800, show_spinner=False)
def get_korean_after_market_data():
    co_buy = []
    after_hours = []

    try:
        # 외국인 매수 상위 (네이버 긁어오기)
        res_f = requests.get("https://finance.naver.com/sise/sise_deal_rank_iframe.naver?sosok=01&investor_gubun=9000&type=1", headers=headers)
        soup_f = BeautifulSoup(res_f.text, 'html.parser')
        for row in soup_f.select('table.type_1 tr')[:4]:
            cols = row.find_all('td')
            if len(cols) >= 4 and cols[1].find('a'):
                name = cols[1].text.strip()
                amt = cols[3].text.strip()
                co_buy.append({"종목명": name, "특징": f"외국인 매수 상위 ({amt}백만원)"})
                
        # 기관 매수 상위 (네이버 긁어오기)
        res_i = requests.get("https://finance.naver.com/sise/sise_deal_rank_iframe.naver?sosok=01&investor_gubun=1000&type=1", headers=headers)
        soup_i = BeautifulSoup(res_i.text, 'html.parser')
        for row in soup_i.select('table.type_1 tr')[:3]:
            cols = row.find_all('td')
            if len(cols) >= 4 and cols[1].find('a'):
                name = cols[1].text.strip()
                amt = cols[3].text.strip()
                co_buy.append({"종목명": name, "특징": f"기관 매수 상위 ({amt}백만원)"})
    except:
        co_buy.append({"종목명": "데이터 수집 지연", "특징": "네이버 수급 데이터 오류"})

    try:
        # 당일 코스피 급등주 (네이버 긁어오기)
        res_up = requests.get("https://finance.naver.com/sise/sise_rise.naver?sosok=0", headers=headers)
        soup_up = BeautifulSoup(res_up.text, 'html.parser')
        count = 0
        for row in soup_up.select('table.type_2 tr'):
            cols = row.find_all('td')
            if len(cols) >= 5 and cols[1].find('a'):
                name = cols[1].text.strip()
                pct = cols[4].text.strip()
                after_hours.append({"종목명": name, "상승률": f"+{pct}%", "특징": "당일 정규장 폭등"})
                count += 1
                if count >= 3: break
    except:
        after_hours.append({"종목명": "데이터 수집 지연", "상승률": "-", "특징": "급등주 파악 지연"})

    return co_buy, after_hours

# ==========================================
# 3. 메인 실행 버튼 및 AI 작문 엔진
# ==========================================
btn_text = "🌅 미장 모닝 브리핑 굽기" if "미국" in target_market else "🌇 국장 마감 & 내일 전략 굽기"

if st.button(btn_text, use_container_width=True):
    with st.spinner(f"데이터와 뉴스를 싹쓸이하여 {target_market} 전문 전략 보고서를 작성 중입니다... ☕ (캐싱 적용으로 약 10초 소요)"):
        
        index_data = get_index_data(target_market)
        major_data = get_major_stocks_data(target_market)
        news_data = get_market_news(target_market)

        korean_supply_data = ""
        search_rank_info = ""
        
        if "한국" in target_market:
            co_buy, after_hours = get_korean_after_market_data()
            co_buy_str = "\n".join([f"  - {item['종목명']} ({item['특징']})" for item in co_buy])
            after_hours_str = "\n".join([f"  - {item['종목명']} : {item['상승률']} ({item['특징']})" for item in after_hours])
            korean_supply_data = f"\n- 4. 세력(외인/기관) 매수 특징주: \n{co_buy_str}\n- 5. 당일 급등 특징주: \n{after_hours_str}"
            
            # 💡 [업그레이드] 한국 증시일 경우 실시간 검색 랭킹 데이터를 AI에게 주입
            rank_str = get_naver_search_ranks_string()
            if rank_str:
                search_rank_info = f"\n[🔥 현재 네이버 실시간 검색 상위 종목]\n{rank_str}\n"
        
        insight_focus = "오늘 한국 증시에 미칠 영향" if "미국" in target_market else "내일 시장 대비, 낙수효과 테마 및 향후 주도주 전략"
        
        prompt = f"""
        당신은 월스트리트 출신의 전문 투자 분석가이자 주식 블로그 '앤트리치'의 수석 에디터입니다. 
        오늘 수집된 팩트 데이터를 바탕으로, 블로그 독자들을 매료시킬 강력한 시황 브리핑을 작성해 주세요.

        [오늘의 팩트 데이터 ({target_market})]
        - 1. 주요 지수 마감 현황: \n{index_data}
        - 2. 시장 주도주(대표주) 주가 현황: \n{major_data}
        - 3. 시장 핫이슈 및 특징 뉴스 종합: \n{news_data} {korean_supply_data}
        {search_rank_info}

        [🚨 매우 중요한 작성 규칙 및 양식 (가독성 극대화)]
        1. [어투 종결 강제]: 1번~4번 항목까지의 문장 끝은 무조건 "~함", "~됨", "~했음", "~예상됨", "~필요함" 형식의 전문적인 개조식으로만 작성하세요. 
        2. [팩트 강조]: 강조 시 별표(*) 대신 대괄호([ ])나 꺾쇠(【 】)를 사용하세요.
        3. [기호 통제]: 글 전체에 걸쳐 별표(*) 기호와 이모티콘(이모지)은 단 한 개도 절대 사용하지 마세요.
        4. [가독성 및 줄바꿈 강제]: 항목(1~7번)의 제목을 적은 후, **절대 제목 바로 옆에 내용을 이어 적지 마세요.** 무조건 엔터(Enter)를 쳐서 다음 줄로 내린 뒤 하이픈(-)으로 내용을 시작하세요. 또한 내용이 길어질 경우 문맥에 맞게 중간중간 엔터를 쳐서 문단을 나누세요.
        5. [검색 랭킹 최우선]: 한국 증시의 경우 제공된 [네이버 실시간 검색 상위 종목]에 포함된 종목이 특징주나 이슈에 있다면, 브리핑 시 최우선으로 언급하고 종목명 옆에 괄호로 (검색 X위)를 반드시 표기하세요.

        [출력 필수 구성 (순서대로 엄수할 것)]
        1. 블로그 보고서 제목 3가지
        - (블로그 검색(SEO)에 유리하고 호기심을 끄는 제목 3가지를 하이픈으로 나누어 작성)
        
        2. 금일 시장 1줄 요약
        - (시장의 전체적인 흐름을 날카롭게 1줄 요약)
        
        3. 지수 및 특징주 심층 분석
        - (뉴스 데이터와 주가 데이터를 연결하여 인과관계를 명확히 분석. 검색 상위 종목 최우선 반영)
        
        4. 앤트리치의 액션 플랜
        - ({insight_focus}에 대한 구체적이고 전문적인 투자 전략 제안)
        
        5. 🎨 이미지 AI용 주문서
        - 아래 문장을 그대로 똑같이 출력하세요:
          "이 브리핑 내용에 맞는 블로그 썸네일용 만화 이미지 3개 만들어 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘."
          
        6. 🔥 앤트리치의 찐 속마음 (인간미 코멘트)
        - (보고를 마친 후 분위기를 확 바꿔 3040 직장인 개미 투자자에게 빙의해 작성. 비표준어, 한탄, 유머, 인터넷 커뮤니티 말투를 섞어서 아주 찰지고 주관적인 코멘트를 2~3줄 툭 던지듯 작성. AI 느낌 완벽 제거)
        
        7. 블로그용 핵심 태그
        - (핵심 키워드 10~15개를 쉼표로 구분하여 한 줄로 작성)
        """
        
        try:
            response = model.generate_content(prompt)
            st.success(f"🎉 무제한 엔진(Tier 1)을 가동하여 100% 팩트 기반의 {target_market} 전략 보고서를 완성했습니다!")
            
            # 💡 [핵심] 파이썬 물리적 살균 (별표 및 이모티콘 완벽 제거)
            clean_text = response.text.replace("*", "")
            clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text)
            
            with st.container(border=True):
                st.markdown(clean_text)
                
        except Exception as e:
            st.error(f"🚨 일시적인 네트워크 오류가 발생했습니다: {e}")
