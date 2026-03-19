import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import urllib.request
import urllib.parse
import json

# ==========================================
# 0. AI 및 위장 신분증 세팅
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

st.set_page_config(page_title="앤트리치 테마주 분석 보고서", page_icon="🎯")

# ==========================================
# 🚨 블로그 우회 접속 차단기 (암살자 모드)
# ==========================================
if "passed" not in st.session_state:
    st.session_state.passed = False

if st.query_params.get("from") == "blog":
    st.session_state.passed = True
    st.query_params.clear()

if not st.session_state.passed:
    st.error("🚨 비정상적인 접근입니다!")
    st.write("이 **[앤트리치 테마주 심층 분석]**은 블로그 방문자 전용 프리미엄 기능입니다.")
    st.write("아래 버튼을 눌러 블로그를 통해 정식으로 접속해 주세요! 🐜")
    st.link_button("👉 앤트리치 블로그로 이동하기", "https://blog.naver.com/antrich10")
    st.stop()
# ==========================================

st.title("🎯 테마주 핵심 수혜주 분석 보고")
st.write("실시간 시장 뉴스를 취합하여 해당 테마의 대장주 및 관련주 동향을 즉시 보고합니다.")
st.divider()

# ==========================================
# 🧠 [듀얼 엔진] 네이버 + 구글 뉴스 결합 캐싱
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_theme_stocks(theme):
    news_results = []
    
    # ----------------------------------------
    # 엔진 1: 네이버 뉴스 API
    # ----------------------------------------
    try:
        client_id = st.secrets["NAVER_CLIENT_ID"]
        client_secret = st.secrets["NAVER_CLIENT_SECRET"]
        query = urllib.parse.quote(f"{theme} 특징주 OR 대장주 OR 수혜주")
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=sim"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)
        
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            data = json.loads(response.read().decode('utf-8'))
            for item in data['items']:
                clean_title = BeautifulSoup(item['title'], 'html.parser').text
                news_results.append(f"[네이버 뉴스] {clean_title}")
    except Exception as e:
        pass

    # ----------------------------------------
    # 엔진 2: 구글 뉴스 RSS
    # ----------------------------------------
    try:
        url_google = f"https://news.google.com/rss/search?q={theme} 주식 수혜주 when:7d&hl=ko&gl=KR&ceid=KR:ko"
        res_google = requests.get(url_google, headers=headers)
        soup_google = BeautifulSoup(res_google.text, "html.parser")
        
        for news in soup_google.find_all("item")[:10]:
            news_results.append(f"[구글 뉴스] {news.title.text}")
    except Exception as e:
        pass

    news_text = "\n".join(news_results) if news_results else "최근 뚜렷한 특징주 뉴스가 없습니다. 일반적인 시장 지식을 활용해 답변하세요."

    # ----------------------------------------
    # 💡 [핵심] 직장 상사 보고용으로 완벽 개조된 프롬프트
    # ----------------------------------------
    prompt = f"""
    당신은 기업의 수석 투자 분석가입니다.
    사용자가 분석을 지시한 주식 테마는 [{theme}] 입니다.
    다음은 실시간으로 수집된 한국 네이버 및 구글의 최신 뉴스 헤드라인 데이터입니다.
    
    {news_text}

    이 데이터를 바탕으로 직장 상사(팀장/본부장)에게 보고하는 형식의 [{theme}] 테마 대장주 및 관련주 분석 보고서를 작성해 주세요.

    [🚨 매우 중요한 작성 규칙 및 양식]
    1. 도입부: 반드시 "본부장님(또는 팀장님), [{theme}] 테마 관련 핵심 수혜주 및 시장 동향 보고드립니다." 로 시작하세요.
    2. 개조식 보고: 불필요한 서론 없이 바로 섹션을 나누어 개조식(~함, ~됨, ~전망)으로 간결하게 보고하세요.
    3. 팩트 강조: 종목명, 핵심 수혜 사유, 주요 수주 내용 등 보고의 핵심 팩트는 반드시 **굵은 글씨(마크다운)**로 강조하세요.
    4. 아래의 마크다운 구조를 엄격하게 지켜서 출력하세요.

    ■ 1. [{theme}] 테마 시장 동향 요약
    - (최근 이 테마가 왜 부각되었는지 뉴스 기반으로 1~2줄 개조식 요약)

    ■ 2. 최선호주 (Top Pick / 대장주)
    - **[종목명]** : (이 종목이 대장주인 명확한 근거 1줄)

    ■ 3. 주요 관련주 동향 (2등주/수혜주)
    - **[종목명]** : (관련주 편입 사유 및 팩트 1줄)
    - **[종목명]** : (관련주 편입 사유 및 팩트 1줄)

    ■ 4. 애널리스트 종합 의견 및 리스크 점검
    - (이 테마의 지속 가능성, 추격 매수 위험성 등에 대한 전문가적 견해 1~2줄 요약 보고)
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
theme_input = st.text_input("🔍 분석을 지시할 테마명을 입력하세요 (예: 원전, 전고체 배터리, 저PBR)", placeholder="테마 키워드를 입력하고 엔터를 치세요!")

# ==========================================
# 2. 버튼 클릭 시 실행
# ==========================================
if st.button("테마주 분석 보고서 출력 🚀", use_container_width=True):
    if not theme_input:
        st.warning("테마 키워드를 먼저 입력해 주세요!")
    else:
        with st.spinner(f"[{theme_input}] 테마 관련 데이터를 취합하여 공식 보고서를 작성 중입니다... 🕵️‍♂️"):
            
            result_text = get_theme_stocks(theme_input)
            
            if result_text == "ERROR_LIMIT":
                st.error("🚨 앗! AI 과부하 상태입니다. 딱 1분만 기다리셨다가 다시 버튼을 눌러주세요!")
            elif result_text == "ERROR_UNKNOWN":
                st.error("🚨 알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
            else:
                st.success(f"✅ [{theme_input}] 테마주 심층 분석 보고서 완성!")
                with st.container(border=True):
                    st.markdown(result_text)

# ==========================================
# 3. 블로그 트래픽 유도용 하단 버튼 & 면책 조항
# ==========================================
st.divider()
st.caption("실제 매매 전 필수 확인! 앤트리치의 심층 분석 리포트를 블로그에서 확인하세요.")
st.link_button("👉 앤트리치 블로그 바로가기", "https://blog.naver.com/antrich10", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True) 

# 💡 굵은 빨간색 면책 조항
st.markdown("""
<div style="color: red; font-weight: bold; font-size: 13px; text-align: center;">
[투자 유의사항]<br>
본 보고서는 정보 제공을 목적으로 자동 작성되었으며, 특정 종목의 매수/매도 추천이 아닙니다.<br>
투자에 대한 모든 판단과 책임은 투자자 본인에게 있음을 알려드립니다.
</div>
""", unsafe_allow_html=True)
