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

st.set_page_config(page_title="앤트리치 테마주 족집게", page_icon="🎯")

# ==========================================

st.title("🎯 주식 관련주/수혜주 찾기")
st.write("앤트리치가 실시간 뉴스를 싹쓸이 분석해 '진짜 수혜주'만 3초 만에 쏙쏙 골라드립니다.")
st.divider()

# ==========================================
# 🧠 [듀얼 엔진] 네이버 + 구글 뉴스 결합 캐싱
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_theme_stocks(theme):
    news_results = []
    
    # ----------------------------------------
    # 엔진 1: 네이버 뉴스 API (실시간 속보 및 찌라시 포착)
    # ----------------------------------------
    try:
        client_id = st.secrets["NAVER_CLIENT_ID"]
        client_secret = st.secrets["NAVER_CLIENT_SECRET"]
        # 검색어 세팅: 테마 이름 + 특징주/대장주
        query = urllib.parse.quote(f"{theme} 특징주 OR 대장주 OR 수혜주")
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=sim"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)
        
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            data = json.loads(response.read().decode('utf-8'))
            for item in data['items']:
                # 네이버 API는 제목에 HTML 태그(<b>)를 섞어서 주므로 깔끔하게 제거
                clean_title = BeautifulSoup(item['title'], 'html.parser').text
                news_results.append(f"[네이버 뉴스] {clean_title}")
    except Exception as e:
        pass # 네이버 에러 나면 조용히 패스하고 구글로 넘어감

    # ----------------------------------------
    # 엔진 2: 구글 뉴스 RSS (글로벌 트렌드 및 거시적 시각 포착)
    # ----------------------------------------
    try:
        url_google = f"https://news.google.com/rss/search?q={theme} 주식 수혜주 when:7d&hl=ko&gl=KR&ceid=KR:ko"
        res_google = requests.get(url_google, headers=headers)
        soup_google = BeautifulSoup(res_google.text, "html.parser")
        
        for news in soup_google.find_all("item")[:10]:
            news_results.append(f"[구글 뉴스] {news.title.text}")
    except Exception as e:
        pass

    # 두 엔진에서 긁어온 뉴스 합치기
    news_text = "\n".join(news_results) if news_results else "최근 뚜렷한 특징주 뉴스가 없습니다. 일반적인 시장 지식을 활용해 답변하세요."

    # ----------------------------------------
    # AI 전문가 분석 프롬프트
    # ----------------------------------------
    prompt = f"""
    당신은 '앤트리치' 주식 블로그의 테마주 발굴 전문가입니다.
    사용자가 궁금해하는 주식 테마는 [{theme}] 입니다.
    다음은 한국 네이버 뉴스와 구글 뉴스에서 방금 수집된 실시간 뉴스 헤드라인입니다.
    
    {news_text}

    이 듀얼 엔진 뉴스 정보와 당신의 주식 시장 지식을 완벽하게 종합하여, 현재 시장에서 [{theme}] 테마를 이끄는 '진짜 대장주(1개)'와 '관련주/2등주(2개)'를 꼽아주세요.

    [작성 규칙]
    1. 쓸데없는 인사말 없이 즉시 답변을 시작하세요.
    2. 왜 이 종목이 수혜주로 꼽히는지 기사 팩트 기반의 '1줄 이유'를 반드시 적어주세요.
    3. 아래 마크다운 양식을 정확히 지켜서 출력하세요.

    ### 🥇 [{theme}] 대장주 (Top Pick)
    - **[종목명]** : (이 종목이 대장주인 팩트 1줄 이유)

    ### 🥈 [{theme}] 관련주 / 2등주
    1. **[종목명]** : (수혜주로 꼽히는 팩트 1줄 이유)
    2. **[종목명]** : (수혜주로 꼽히는 팩트 1줄 이유)

    ### 💡 앤트리치 코멘트 (투자 유의사항)
    - (이 테마에 투자할 때 주의할 점이나 재료의 지속성에 대한 분석가 코멘트 1~2줄)
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
theme_input = st.text_input("🔍 궁금한 테마를 입력하세요 (예: 원전, 전고체 배터리, 비만치료제, 저PBR)", placeholder="테마 키워드를 입력하고 엔터를 치세요!")

# ==========================================
# 2. 버튼 클릭 시 실행
# ==========================================
if st.button("대장주 찾기 🚀", use_container_width=True):
    if not theme_input:
        st.warning("테마 키워드를 먼저 입력해 주세요!")
    else:
        with st.spinner(f"앤트리치가 뉴스를 싹쓸이하여 [{theme_input}] 진짜 수혜주를 색출 중입니다..."):
            
            result_text = get_theme_stocks(theme_input)
            
            if result_text == "ERROR_LIMIT":
                st.error("🚨 앗! AI가 생각할 시간을 달래요. 딱 1분만 기다리셨다가 다시 버튼을 눌러주세요!")
            elif result_text == "ERROR_UNKNOWN":
                st.error("🚨 알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
            else:
                st.success(f"✅ [{theme_input}] 테마주 족집게 분석 완료!")
                with st.container(border=True):
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
