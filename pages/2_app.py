import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import warnings
from google.api_core.exceptions import ResourceExhausted
import urllib.request
import urllib.parse
import json

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# ==========================================
# 0. AI 세팅
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

st.set_page_config(page_title="앤트리치 봇", page_icon="🐜")
st.title("🐜 앤트리치 블로그 자동화 봇")
st.write("클릭 몇 번으로 핫한 종목을 찾고, 사람 냄새 풀풀 나는 포스팅 초안을 완성하세요!")

st.divider()

# --- [1단계] 실시간 핫스탁 검색 (듀얼 엔진) ---
st.header("🔍 1. 실시간 인기 종목 찾기")
market = st.radio("어떤 시장을 검색할까요?", ["한국 증시", "미국 증시"], horizontal=True)

if st.button("핫스탁 검색하기"):
    with st.spinner("네이버와 구글에서 최신 뉴스를 싹쓸이하는 중입니다... 잠시만 기다려주세요! 🚀"):
        hot_news_titles = []
        
        # [엔진 1] 한국 증시면 네이버 뉴스 출동!
        if "한국" in market:
            try:
                client_id = st.secrets["NAVER_CLIENT_ID"]
                client_secret = st.secrets["NAVER_CLIENT_SECRET"]
                query = urllib.parse.quote("특징주 OR 상한가 OR 수혜주")
                url_naver = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=sim"
                
                request = urllib.request.Request(url_naver)
                request.add_header("X-Naver-Client-Id", client_id)
                request.add_header("X-Naver-Client-Secret", client_secret)
                
                response_naver = urllib.request.urlopen(request)
                if response_naver.getcode() == 200:
                    data = json.loads(response_naver.read().decode('utf-8'))
                    for item in data['items']:
                        clean_title = BeautifulSoup(item['title'], 'html.parser').text
                        hot_news_titles.append(f"[네이버 속보] {clean_title}")
            except Exception as e:
                pass 

        # [엔진 2] 구글 뉴스 출동! (한국/미국 공통)
        try:
            if "한국" in market:
                search_keyword = "한국 증시 특징주 OR 코스피 특징주 when:1d"
            else:
                search_keyword = "미국 증시 특징주 OR 서학개미 인기 when:1d"
                
            url_google = f"https://news.google.com/rss/search?q={search_keyword}&hl=ko&gl=KR&ceid=KR:ko"
            response_google = requests.get(url_google, headers=headers)
            soup_google = BeautifulSoup(response_google.text, "html.parser")
            
            for news in soup_google.find_all("item")[:10]: 
                hot_news_titles.append(f"[구글 뉴스] {news.title.text}")
        except Exception as e:
            pass

        if not hot_news_titles:
            st.error("🚨 서버에서 뉴스를 주지 않았습니다. 잠시 후 다시 시도해 주세요!")
        else:
            hot_news_text = "\n".join(hot_news_titles)

            list_prompt = f"""
            다음은 한국과 미국의 최근 주식 시장 뉴스 제목들이야.
            {hot_news_text}
            이 뉴스들을 분석해서 오늘 사람들이 가장 많이 관심을 가진 종목 5개를 찾아서 리스트로 정리해 줘. (종목명 - 이유 1줄 형식)
            """
            
            try:
                list_response = model.generate_content(list_prompt)
                st.success("✅ 검색 완료!")
                st.markdown(list_response.text)
            except ResourceExhausted:
                st.error("🚨 앗! AI가 생각할 시간을 달래요. 딱 1분만 이따가 다시 눌러주세요!")

st.divider()

# --- [2단계] 포스팅 초안 생성 ---
st.header("✍️ 2. 블로그 포스팅 초안 만들기")
target_stock = st.text_input("위에서 찾은 종목이나, 다루고 싶은 종목 이름을 입력하세요:")

if st.button("만화 대본 & 포스팅 작성하기🚀"):
    if target_stock == "":
        st.warning("종목 이름을 먼저 입력해 주세요!")
    else:
        with st.spinner(f"[{target_stock}] 휴먼 모드 작가에 빙의하여 완벽한 초안을 작성 중입니다... ✍️"):
            target_news_titles = []
            
            # [엔진 1] 네이버 뉴스 싹쓸이 (본문 요 초 포함)
            try:
                client_id = st.secrets["NAVER_CLIENT_ID"]
                client_secret = st.secrets["NAVER_CLIENT_SECRET"]
                query = urllib.parse.quote(f"{target_stock} 주식 OR 특징주")
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
                        target_news_titles.append(f"[네이버] 제목: {clean_title} / 요약: {clean_desc}")
            except Exception as e:
                pass

            # [엔진 2] 구글 뉴스 싹쓸이
            try:
                url_target = f"https://news.google.com/rss/search?q={target_stock} 주식 when:1d&hl=ko&gl=KR&ceid=KR:ko"
                response_target = requests.get(url_target, headers=headers)
                soup_target = BeautifulSoup(response_target.text, "html.parser")
                
                for news in soup_target.find_all("item")[:10]:
                    target_news_titles.append(f"[구글] 제목: {news.title.text}")
            except Exception as e:
                pass

            if not target_news_titles:
                 st.error(f"🚨 '{target_stock}'에 대한 최신 뉴스를 찾지 못했습니다. 종목명을 다시 확인해 주세요!")
            else:
                target_news_text = "\n".join(target_news_titles)

                # ==========================================
                # 🧠 100% 휴먼 블로거 모드로 개조된 프롬프트!
                # ==========================================
                script_prompt = f"""
                당신은 절대 AI가 아닙니다. 
                당신은 현재 초등학교 4학년, 2학년 두 아들을 키우는 40대 평범한 직장인이자, 
                2026년 12월까지 금융자산 1억 원 달성을 위해 매일 치열하게 주식 시장과 씨름하는 '앤트리치(Antrich)' 블로그의 실제 주인입니다.

                절대 기계나 AI가 쓴 글처럼 보이지 않도록, 친한 주식 투자 동료나 이웃 블로거들에게 커피 한 잔 마시며 썰을 풀듯 아주 자연스럽고 맛깔나는 사람의 문장으로 포스팅을 작성해 주세요.

                다음은 '{target_stock}' 주식에 대해 수집한 최신 뉴스들입니다:
                {target_news_text}
                
                🚨 [매우 중요한 작성 규칙 및 톤앤매너]
                1. [AI 금지어]: "요약하자면", "결론적으로", "이 글에서는", "주의가 필요합니다", "살펴보겠습니다", "기대됩니다" 등 전형적인 AI 문구 절대 사용 금지!
                2. [사람 냄새]: "애들 학원비 벌려다 물렸네요~", "주주분들 오늘 밤잠 설치시겠네요", "슈팅이 나왔네요", "줍줍" 등 40대 가장 느낌과 주식 커뮤니티 은어를 문맥에 맞게 자연스럽게 섞어주세요.
                3. [글 구조]: 기계적인 요약표나 넘버링(1번, 2번 등)을 쓰지 말고, 블로거가 독자에게 말 거는 듯한 자연스러운 단락(줄글)으로 작성하세요.
                4. [만화 대사 규칙]: 만화 대본 작성 시 대사 부분에는 화자 이름(예: (개미 1))을 절대 적지 말고, 오직 말하는 내용만 큰따옴표 안에 적어 주세요.
                
                [출력해야 할 완벽한 블로그 초안 구성]
                1. [블로그 제목 추천]: 검색 유입과 호기심을 동시에 잡는 인간적인 어그로 제목 3가지
                2. [도입부 및 오늘의 핫이슈 썰 풀기]: 오늘 이 종목에 왜 난리가 났는지 뉴스를 바탕으로 사람 냄새 나는 썰 풀기로 시작 (예: "오늘 장 보다가 깜짝 놀랐습니다~")
                3. [10컷 만화 대본]: 개미 캐릭터들이 등장하는 10컷 대본 (각 컷별 이미지 생성 지시문과 대사 필수. 지시문에는 반드시 해당 컷의 대사가 이미지 안에 말풍선 텍스트로 포함되도록 영어로 명령할 것.)
                4. [관련 수혜주 및 앤트리치 인사이트]: 엮인 테마주 설명과 함께, 2026년 1억 달성을 향해 달려가는 40대 가장 앤트리치의 찐 관점과 대응 전략을 공감 가도록 줄글로 작성
                5. [바쁜 현대인을 위한 3초 결론 박스]: 이 종목에 대한 핵심 요약 3줄
                6. [블로그 입력용 태그 리스트]: 관련 해시태그 20개를 쉼표(,)로 구분한 형태
                7. [🎨 제미나이 복사/붙여넣기용 이미지 생성 명령어]: 포스팅 맨 마지막에 아래 텍스트를 정확하게 출력할 것.
                   "위 만화 대본을 바탕으로 이미지 10장을 생성해 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘."
                """
                
                try:
                    script_response = model.generate_content(script_prompt)
                    st.success("✅ 사람 냄새 풀풀 나는 포스팅 초안이 완성되었습니다!")
                    with st.container(border=True):
                        st.markdown(script_response.text)
                except ResourceExhausted:
                    st.error("🚨 앗! AI 과부하 상태입니다. 딱 1분만 기다리셨다가 다시 버튼을 눌러주세요!")
