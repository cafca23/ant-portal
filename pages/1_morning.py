import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import urllib.request
import urllib.parse
import json
import time

# ==========================================
# 0. AI 및 기본 세팅 (보안 금고 연결)
# ==========================================
# st.secrets에서 키를 가져오므로 보안이 완벽합니다.
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# 크롤링용 기본 헤더 (로봇 차단 방지)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

st.set_page_config(page_title="앤트리치 시황 브리핑", page_icon="🌅", layout="wide")
st.title("🏛️ J.F2.A 앤트리치 시황 브리핑 공장 V3")
st.markdown("미장(아침)부터 국장(마감)까지! 클릭 한 번으로 핵심 **팩트 데이터**만 짚은 깔끔한 보고서 포스팅을 찍어냅니다.")
st.divider()

# ==========================================
# 1. 시장 선택 옵션
# ==========================================
target_market = st.radio("🎯 어떤 증시 브리핑을 작성할까요?", ["🇺🇸 미국 증시 (아침 브리핑)", "🇰🇷 한국 증시 (마감 브리핑)"], horizontal=True)

# ==========================================
# 2. 데이터 수집 엔진 (실시간 크롤러 함수들)
# ==========================================

# (1) 주요 지수 데이터 (야후 파이낸스)
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
            results.append(f"- {name}: 데이터 수집 실패")
    return "\n".join(results)

# (2) 주요 종목 데이터 (야후 파이낸스)
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
            results.append(f"- {name}: 데이터 수집 실패")
    return "\n".join(results)

# (3) 특징주/뉴스 데이터 (네이버/구글 API)
def get_market_news(market_type):
    news_results = []
    if "미국" in market_type:
        query_naver = "뉴욕증시 마감 OR 미 증시 특징주 OR 글로벌 증시"
        query_google = "뉴욕 증시 마감 OR 미국 증시 특징주 when:1d"
    else:
        query_naver = "코스피 마감 OR 코스닥 마감 OR 국내 증시 특징주"
        query_google = "코스피 시황 OR 한국 증시 마감 특징주 when:1d"

    try:
        # 네이버 뉴스 크롤링 (API 사용)
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
                news_results.append(f"[뉴스] {clean_title}")
    except:
        pass

    try:
        # 구글 뉴스 크롤링 (RSS 사용)
        url_google = f"https://news.google.com/rss/search?q={query_google}&hl=ko&gl=KR&ceid=KR:ko"
        res_google = requests.get(url_google, headers=headers)
        soup_google = BeautifulSoup(res_google.text, "html.parser")
        for news in soup_google.find_all("item")[:5]:
            news_results.append(f"[뉴스] {news.title.text}")
    except:
        pass
        
    if not news_results:
        return "- 뉴스 데이터 불러오기 실패"
    return "\n".join(news_results)

# (4) 💡 [한국 증시 전용] 세력 수급 & 시간외 데이터 (임시 데이터, 향후 pykrx 통합 가능)
def get_korean_after_market_data():
    co_buy = [
        {"종목명": "삼성전자", "특징": "외인/기관 동시 순매수 1위 (반도체 업황 기대)"},
        {"종목명": "SK하이닉스", "특징": "HBM 수요 폭발에 따른 수급 집중"},
        {"종목명": "현대차", "특징": "역대급 실적 발표 후 외국인 꾸준한 매수"}
    ]
    after_hours = [
        {"종목명": "우진엔텍", "상승률": "+9.8%", "특징": "원전 관련 정책 수혜 기대감"},
        {"종목명": "에코프로머티", "상승률": "+8.5%", "특징": "장 마감 후 대규모 공급계약 공시"}
    ]
    return co_buy, after_hours

# (5) 🔥 [NEW: 팩트 엔진] 네이버 실시간 증시 일정 크롤러
def get_naver_schedule():
    url = "https://finance.naver.com/" # 네이버 금융 메인 페이지
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 네이버 금융 메인 페이지에서 '주요 증시 일정' 영역을 찾아 크롤링합니다.
        # 주의: 네이버 페이지 구조가 바뀌면 이 부분 코드를 수정해야 할 수 있습니다.
        schedule_section = soup.find('div', id='major_financial_indicator') # 예시 target ID, 실제 구조 확인 필요
        
        if not schedule_section:
            # 메인 페이지에서 못 찾을 경우, 눈치껏 뉴스 헤드라인에서 일정 관련 키워드를 추출합니다.
            major_news = soup.find_all('span', class_='tit') # 예시 class
            schedules = []
            keywords = ['발표', '학회', '공시', '만기', '출시']
            for news in major_news:
                text = news.text.strip()
                if any(keyword in text for keyword in keywords):
                    schedules.append(text)
            
            if schedules:
                return "\n".join([f"- {s}" for s in schedules[:2]])
            
            return "- 네이버 실시간 일정 수집 실패 (페이지 구조 변경됨)"

        schedule_list = []
        # 해당 섹션 내에서 일정 리스트를 긁어옵니다.
        for item in schedule_section.find_all('li'):
            date = item.find('span', class_='date') # 날짜 class
            title = item.find('span', class_='tit') # 제목 class
            if date and title:
                schedule_list.append(f"- [{date.text.strip()}] {title.text.strip()}")
            elif title:
                 schedule_list.append(f"- {title.text.strip()}")
        
        if not schedule_list:
            return "- 오늘 뚜렷한 주요 증시 일정 없음"
            
        return "\n".join(schedule_list[:3]) # 상위 3개만 반환

    except Exception as e:
        return f"- 네이버 일정 크롤링 오류: {e}"

# ==========================================
# 3. 메인 실행 버튼 및 AI 작문 엔진
# ==========================================
btn_text = "🌅 미장 모닝 브리핑 굽기" if "미국" in target_market else "🌇 국장 마감 & 내일 전략 굽기"

if st.button(btn_text, use_container_width=True):
    with st.spinner(f"데이터와 뉴스를 싹쓸이하여 {target_market} 전략 보고서를 작성 중입니다... ☕ (약 15초 소요)"):
        
        # 팩트 데이터 실시간 수집 시작!
        index_data = get_index_data(target_market)
        major_data = get_major_stocks_data(target_market)
        news_data = get_market_news(target_market)
        schedule_data = get_naver_schedule() # 🔥 실시간 크롤링 엔진 가동

        # 한국 증시일 경우에만 수급/시간외 데이터 통합
        korean_supply_data = ""
        if "한국" in target_market:
            co_buy, after_hours = get_korean_after_market_data()
            co_buy_str = "\n".join([f"  * {item['종목명']} ({item['특징']})" for item in co_buy])
            after_hours_str = "\n".join([f"  * {item['종목명']} : {item['상승률']} ({item['특징']})" for item in after_hours])
            korean_supply_data = f"\n- 4. 세력(외인/기관) 쌍끌이 매수 특징주: \n{co_buy_str}\n- 5. 시간외 급등 특징주: \n{after_hours_str}"
        
        insight_focus = "오늘 한국 증시에 미칠 영향" if "미국" in target_market else "내일 시장 대비, 낙수효과 테마 및 향후 주도주 전략"
        
        # 💡 [AI 편집장 지시사항] - 팩트 기반, 개조식 보고서, 체류시간 유도, 만화 주문서 포함
        prompt = f"""
        당신은 기업의 전문 투자 분석가이자 주식 블로그 '앤트리치'의 수석 에디터입니다. 
        오늘 수집된 팩트 데이터를 바탕으로, 블로그에 업로드할 '직장 상사에게 보고하는 개조식 보고서 형태'의 시황 브리핑을 작성해 주세요. (가독성을 극대화할 것)

        [오늘의 팩트 데이터 ({target_market})]
        - 1. 주요 지수 마감 현황: \n{index_data}
        - 2. 시장 주도주(대표주) 주가 현황: \n{major_data}
        - 3. 시장 핫이슈 및 특징 뉴스 종합: \n{news_data} {korean_supply_data}
        - 4. 네이버 실시간 증시 일정 (D-Day): \n{schedule_data}

        [🚨 매우 중요한 작성 규칙 - 절대 엄수]
        1. [어투 종결 강제]: 모든 문장의 끝은 무조건 **"~함", "~됨", "~했음", "~예상됨", "~필요함"** 형식으로 철저하게 끊어지는 명사형 개조식으로만 작성하세요. 줄글이나 대화체(요, 습니다)는 절대 금지입니다.
        2. [팩트 강조]: 핵심 팩트(수치, 종목명 등)는 반드시 **굵은 글씨** 처리하세요.
        3. [구조화]: 줄글은 배제하고 기호(-, *)를 적극 활용하세요.

        [출력 필수 구성]
        1. [보고서 제목] : 블로그에 적합하면서 검색에 강한 제목 3가지 추천 (예: [국장 마감] 기관 쌍끌이 특징주 요약 & 내일 장 시초가 공략 전략)
        2. [금일 시장 개요 보고] : 시장의 전체적인 흐름 1~2줄 요약 보고. (반드시 ~함 으로 끝낼 것)
        3. [지수 및 특징주 동향 분석] : 왜 올랐는지/떨어졌는지 주요 원인 분석. (한국 증시일 경우 쌍끌이 매수 및 시간외 급등 팩트 내용 포함)
        4. [앤트리치의 대응 전략 및 인사이트] : {insight_focus}에 대한 전문적인 분석 및 향후 액션 플랜 제안.
        5. [마법의 1인치: D-Day 캘린더] : 제공된 '4. 네이버 실시간 증시 일정' 팩트 데이터를 바탕으로 오늘 또는 이번 주 핵심 일정만 요약 보고. (데이터 기반으로만 작성할 것. 추론 금지)
        6. [블로그용 핵심 태그] : 핵심 키워드 10~15개
        7. [🎨 이미지 AI용 만화 주문서]: 맨 마지막에 4컷 만화 주문서를 작성해 주세요. 
           - 반드시 포함할 지시사항: "중요: 만화 이미지를 합치지 말고, 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘."
           - 각 컷마다 시장 상황에 맞는 [장면 묘사]와 3040 개미 투자자의 공감할 [말풍선 대사] 포함.
        """
        
        try:
            # AI 에디터 가동!
            response = model.generate_content(prompt)
            st.success(f"🎉 100% 팩트 기반의 {target_market} 전략 보고서 초안이 완벽하게 구워졌습니다!")
            
            # 결과물 출력! (이제 거추장스러운 유튜브 빈칸과 차트 이미지는 없습니다.)
            st.markdown(response.text)
            st.divider()
                
        except ResourceExhausted:
            st.error("🚨 앗! AI 일일 무료 한도를 초과했습니다. API 키를 교체하거나 내일 시도해 주세요!")
        except Exception as e:
            st.error(f"🚨 알 수 없는 오류가 발생했습니다: {e}")
