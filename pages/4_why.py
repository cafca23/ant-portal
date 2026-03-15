import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
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

st.set_page_config(page_title="앤트리치 종목 이유 판독기", page_icon="🚨")

# ==========================================


st.title("🚨 이 종목 왜 상승 / 하락 했지?")
st.write("앤트리치가 실시간 뉴스를 싹쓸이해서 급등락 이유를 딱 3줄로 요약해 드립니다.")

# 💡 [신규 추가] 사용자 안내 문구 (파란색 예쁜 박스로 강조!)
st.info("💡 참고: 최근 24시간 동안 특별한 뉴스가 없는 종목은 검색 결과가 안 나와요!")

st.divider()

# ==========================================
# 🧠 [핵심 마법] 1시간 기억하는 AI 두뇌 (듀얼 엔진 캐싱)
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_reason(stock_keyword):
    news_results = []
    
    # ----------------------------------------
    # [엔진 1] 네이버 뉴스 싹쓸이 (본문 요약 포함)
    # ----------------------------------------
    try:
        client_id = st.secrets["NAVER_CLIENT_ID"]
        client_secret = st.secrets["NAVER_CLIENT_SECRET"]
        query = urllib.parse.quote(f"{stock_keyword} 특징주 OR 주가 OR 급등 OR 급락")
        url_naver = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=sim"
        
        request = urllib.request.Request(url_naver)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)
        
        response_naver = urllib.request.urlopen(request)
        if response_naver.getcode() == 200:
            data = json.loads(response_naver.read().decode('utf-8'))
            for item in data['items']:
                clean_title = BeautifulSoup(item['title'], 'html.parser').text
                clean_desc = BeautifulSoup(item['description'], 'html.parser').text
                news_results.append(f"[네이버] 제목: {clean_title} / 요약: {clean_desc}")
    except Exception as e:
        pass

    # ----------------------------------------
    # [엔진 2] 구글 뉴스 싹쓸이
    # ----------------------------------------
    try:
        url_google = f"https://news.google.com/rss/search?q={stock_keyword} 주식 when:1d&hl=ko&gl=KR&ceid=KR:ko"
        res_google = requests.get(url_google, headers=headers)
        soup_google = BeautifulSoup(res_google.text, "html.parser")
        
        for news in soup_google.find_all("item")[:10]:
            news_results.append(f"[구글] 제목: {news.title.text}")
    except:
        pass
        
    if not news_results:
        return "NO_NEWS"
        
    # 2. AI에게 분석 지시
    news_text = "\n".join(news_results)
    prompt = f"""
    당신은 '앤트리치' 블로그의 수석 주식 분석가입니다.
    다음은 방금 수집된 [{stock_keyword}] 주식의 한국 네이버 및 구글 최신 뉴스 데이터입니다.
    
    {news_text}

    이 듀얼 엔진 뉴스들을 완벽하게 종합 분석해서, 지금 이 종목의 주가가 움직이는(오르거나 내리거나 이슈가 있는) 핵심 팩트(이유)를 딱 '3가지'로만 요약해 주세요.

    [작성 규칙]
    1. 쓸데없는 인사말이나 서론은 무조건 빼고, 바로 1, 2, 3번 번호를 매겨서 이유만 설명하세요.
    2. 바쁜 현대인들이 스마트폰으로 3초 만에 읽고 이해할 수 있도록 아주 쉽고 명확하게 작성하세요.
    3. 마지막 줄에는 "💡 앤트리치 코멘트:"를 달고, 이 이슈가 단기적인 테마인지, 장기적인 실적에 영향을 줄 것인지 분석가의 의견을 딱 한 줄로 덧붙여 주세요.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except ResourceExhausted:
        return "ERROR_LIMIT"
    except Exception as e:
        return "ERROR_UNKNOWN"

# ==========================================
# 1. 사용자 입력 받기
# ==========================================
stock_name = st.text_input("🔍 궁금한 종목명을 입력하세요 (예: 삼성전자, 에코프로, 테슬라)", placeholder="종목명을 입력하고 엔터를 치거나 버튼을 누르세요!")

# ==========================================
# 2. 버튼 클릭 시 실행
# ==========================================
if st.button("이유 찾기 🚀", use_container_width=True):
    if not stock_name:
        st.warning("종목명을 먼저 입력해 주세요!")
    else:
        with st.spinner(f"앤트리치가 [{stock_name}] 주가 변동의 진짜 이유를 분석 중입니다... 🕵️‍♂️"):
            
            result_text = get_stock_reason(stock_name)
            
            if result_text == "ERROR_LIMIT":
                st.error("🚨 앗! 생각할 시간을 주세요. 딱 1분만 기다리셨다가 다시 버튼을 눌러주세요!")
            elif result_text == "ERROR_NEWS":
                st.error("🚨 뉴스 데이터를 불러오는 데 실패했습니다.")
            elif result_text == "NO_NEWS":
                st.info(f"앗! 최근 24시간 동안 [{stock_name}]에 대한 특별한 뉴스가 없습니다. 아직 관련 뉴스가 없습니다.")
            elif result_text == "ERROR_UNKNOWN":
                st.error("🚨 알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
            else:
                st.success(f"✅ [{stock_name}] 원인 분석 완료!")
                with st.container(border=True):
                    st.markdown(f"### 🎯 [{stock_name}] 주가 변동 요인 3줄 요약")
                    st.markdown(result_text)

# ==========================================
# 3. 블로그 트래픽 유도용 하단 버튼 & 면책 조항
# ==========================================
st.divider()
st.caption("테마주 단타 치기 전에 필수 확인! 앤트리치의 시장 분석을 먼저 읽어보세요.")
st.link_button("👉 앤트리치 블로그 바로가기", "https://blog.naver.com/antrich10", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True) # 약간의 여백 띄우기

# 💡 [신규 업데이트] 굵은 빨간색 면책 조항 적용!
st.markdown("""
<div style="color: red; font-weight: bold; font-size: 13px; text-align: center;">
[투자 유의사항]<br>
본 게시물은 정보 제공을 목적으로 작성되었으며, 특정 종목의 매수/매도 추천이 아닙니다.<br>
투자에 대한 모든 판단과 책임은 투자자 본인에게 있음을 알려드립니다.
</div>
""", unsafe_allow_html=True)
