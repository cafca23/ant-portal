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
st.write("클릭 몇 번으로 핫한 종목을 찾고, 완벽한 포스팅 초안을 완성하세요!")

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
                pass # 네이버 실패해도 구글이 있으니 패스

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
                st.error("🚨 앗! AI가 생각할 시간을 달래요. (1분당 15회 무료 제한 초과) 딱 1분만 이따가 다시 눌러주세요!")

st.divider()

# --- [2단계] 포스팅 초안 생성 ---
st.header("✍️ 2. 블로그 포스팅 초안 만들기")
target_stock = st.text_input("위에서 찾은 종목이나, 다루고 싶은 종목 이름을 입력하세요:")

if st.button("만화 대본 & 포스팅 작성하기🚀"):
    if target_stock == "":
        st.warning("종목 이름을 먼저 입력해 주세요!")
    else:
        with st.spinner(f"[{target_stock}] 듀얼 엔진으로 뉴스를 딥다이브하여 완벽한 초안을 작성 중입니다... ✍️"):
            target_news_titles = []
            
            # [엔진 1] 네이버 뉴스 싹쓸이 (본문 요약 포함)
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
                # 🧠 강력하게 업그레이드된 AI 프롬프트!
                # ==========================================
                script_prompt = f"""
                당신은 '앤트리치' 주식 블로그의 수석 작가이자 분석가입니다.
                다음은 '{target_stock}' 주식에 대해 네이버와 구글에서 수집한 최신 뉴스들이야:
                {target_news_text}
                
                이 뉴스들을 바탕으로 '앤트리치 주식 블로그'에 바로 복사해서 붙여넣을 수 있는 완벽한 포스팅 초안을 작성해 줘.
                
                🚨 [매우 중요한 요청사항]
                1. **[만화 대본 이미지 글자 포함 명령]**: 10컷 만화 대본의 각 컷별 '이미지 생성 지시문(프롬프트)'을 작성할 때, **반드시 해당 컷의 대사 내용이 이미지 안에 텍스트(예: 말풍선)로 정확하게 포함되도록** 지시문을 적어 줘. (예: "A comic style image showing a character saying 'It's a limit high!' inside a text bubble.")
                2. **[태그 리스트 출력]**: 포스팅의 맨 마지막 부분에 블로그 입력용 태그 20개를 쉼표(,)로 구분된 깔끔한 리스트 형식으로 출력해 줘. (예: 태그1, 태그2, 태그3)
                3. **[대사 화자 제거]**: 대사 부분에는 '(개미 1)', '(개미 2)' 같은 화자 이름을 절대 적지 말고, 오직 말하는 내용만 큰따옴표 안에 적어 줘. 
                   (❌ 잘못된 예시: 대사: (개미 1) "와 상한가다!")
                   (⭕ 올바른 예시: 대사: "와 상한가다!")
                
                [출력해야 할 완벽한 블로그 초안 구성]
                1. [블로그 제목 추천]: 매력적인 제목 3가지 추천
                2. [오늘의 핫이슈 3줄 요약]: 오늘 왜 난리가 났는지 알기 쉽게 요약
                3. [10컷 만화 대본]: 개미 캐릭터들이 등장하는 10컷 대본 (각 컷별 이미지 생성 지시문과 대사 필수. 지시문에는 대사 텍스트 포함 명령 필수.)
                4. [관련 수혜주 및 테마 체크]: 함께 움직일 관련주 2~3개 소개
                5. [향후 전망 및 앤트리치 인사이트]: 뉴스를 바탕으로 한 주가 전망
                6. [앤트리치의 실제 투자 액션]: 이 종목에 대한 대응 계획. 2026년 자산 1억 달성 목표와 연관 지어서 한 줄 포함.
                7. [바쁜 현대인을 위한 3초 결론 박스]: 핵심 요약과 질문 3줄 (텍스트로 깔끔하게)
                8. [블로그 입력용 태그 리스트]: 관련 해시태그 20개를 쉼표(,)로 구분한 형태
                """
                
                try:
                    script_response = model.generate_content(script_prompt)
                    st.success("✅ 포스팅 초안이 완성되었습니다! 복사해서 블로그에 붙여넣으세요!")
                    # 결과 출력 (박스 테두리 안에 예쁘게)
                    with st.container(border=True):
                        st.markdown(script_response.text)
                except ResourceExhausted:
                    st.error("🚨 앗! AI 과부하 상태입니다. (1분당 15회 제한 초과) 딱 1분만 기다리셨다가 다시 버튼을 눌러주세요!")
