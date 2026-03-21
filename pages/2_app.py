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
st.title("🐜 앤트리치 종목 심층 분석 봇")
st.write("실시간 핫스탁을 발굴하고, 직장 상사에게 보고하는 형태의 각 잡힌 종목 분석 보고서를 즉시 생성합니다.")

st.divider()

# --- [1단계] 실시간 핫스탁 검색 (듀얼 엔진) ---
st.header("🔍 1. 실시간 특징주 동향 파악")
market = st.radio("어떤 시장을 검색할까요?", ["한국 증시", "미국 증시"], horizontal=True)

if st.button("특징주 동향 검색하기"):
    with st.spinner("네이버와 구글에서 최신 시장 동향을 취합 중입니다... 잠시만 기다려주세요! 🚀"):
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
            st.error("🚨 서버 통신 지연. 잠시 후 다시 시도해 주세요!")
        else:
            hot_news_text = "\n".join(hot_news_titles)

            list_prompt = f"""
            당신은 기업의 수석 투자 분석가입니다.
            다음은 수집된 한국/미국 증시의 최근 뉴스 헤드라인입니다.
            {hot_news_text}
            
            이 뉴스들을 분석하여 현재 시장에서 가장 이슈가 되고 있는 특징주 5개를 도출하여, 직장 상사(팀장/본부장)에게 보고하는 형식으로 간결하게 브리핑해 주세요.

            [🚨 작성 규칙]
            1. 도입부는 "본부장님(팀장님), 금일 시장 주요 특징주 동향 보고드립니다."로 시작하세요.
            2. 종목명과 핵심 상승/하락 사유를 개조식(- 함, - 됨)으로 명확히 기재하세요.
            3. 핵심 팩트 및 종목명은 반드시 **굵은 글씨**로 강조하세요.
            """
            
            try:
                list_response = model.generate_content(list_prompt)
                st.success("✅ 시장 동향 요약 완료!")
                st.markdown(list_response.text)
            except ResourceExhausted:
                st.error("🚨 앗! AI 과부하 상태입니다. 딱 1분만 이따가 다시 눌러주세요!")

st.divider()

# --- [2단계] 포스팅 초안 생성 ---
st.header("✍️ 2. 종목 심층 분석 보고서 생성")
target_stock = st.text_input("심층 분석할 종목명을 정확하게 입력하세요 (예: 삼성전자, 엔비디아):")

if st.button("종목 분석 보고서 작성 🚀"):
    if target_stock == "":
        st.warning("종목 이름을 먼저 입력해 주세요!")
    else:
        with st.spinner(f"[{target_stock}] 관련 데이터를 취합하여 공식 보고서를 작성 중입니다... ✍️"):
            target_news_titles = []
            
            # [엔진 1] 네이버 뉴스 싹쓸이
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
                 st.error(f"🚨 '{target_stock}'에 대한 최신 데이터를 찾지 못했습니다. 종목명을 다시 확인해 주세요!")
            else:
                target_news_text = "\n".join(target_news_titles)

                # ==========================================
                # 🧠 [핵심] 캐릭터 고정 및 프롬프트 구조 완벽 반영!
                # ==========================================
                script_prompt = f"""
                당신은 기업의 수석 투자 분석가이자 콘텐츠 기획자입니다.
                다음 수집된 '{target_stock}' 관련 최신 뉴스를 바탕으로, 직장 상사(본부장/팀장)에게 보고하는 비즈니스 톤앤매너를 유지하되 지정된 블로그 포스팅 구조에 맞게 문서를 작성해 주세요.

                [수집된 데이터]
                {target_news_text}
                
                [🚨 매우 중요한 작성 규칙 및 양식]
                - 어투: 철저하게 직장 상사에게 보고하는 비즈니스 포맷(간결한 개조식: ~함, ~됨, ~전망)으로 작성하세요. 
                - 팩트 강조: 주요 수치, 종목명 등 핵심 팩트는 반드시 **굵은 글씨(마크다운)**로 처리하세요.
                - 도입부: 모든 출력의 시작은 "본부장님, [{target_stock}] 관련 심층 분석 보고드립니다."로 시작하세요.
                
                [출력 필수 구성 (순서대로 정확히 지킬 것)]
                [기본 구성] 10컷 만화 대본
                "위 만화 대본을 바탕으로 이미지 10장을 생성해 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘.대사는 이미지안에 넣어서 생성해"
                - 위 문장을 만화 대본 출력 시작 시 가장 먼저 그대로 출력하세요.
                - 10컷 분량의 대본을 작성하세요.
                - 블로그의 일관성을 위해, 모든 컷의 영어 이미지 생성 지시문에는 반드시 '주식 투자하는 만화 캐릭터 개미(Ant)'가 주인공으로 등장하도록 묘사하세요.
                - 각 컷별로 영어 이미지 생성 지시문(대사가 이미지 말풍선에 포함되도록 명령)과 한글 대사를 필수로 포함하세요.
                - 대사 부분에 화자 이름(예: 개미1)은 절대 적지 말고 큰따옴표 안의 대사만 작성할 것.

                1. 블로그 제목 2개: (보고서 형식의 깔끔한 제목 2가지)
                2. 종목 이름 및 회사 소개: (해당 기업의 비즈니스 모델을 간결한 개조식으로 요약)
                3. 종목 재무제표 요약: (알려진 최신 재무 상태나 실적 동향을 팩트 위주로 간략히 보고)
                4. 금일 핫이슈 3줄 요약: (위 뉴스를 바탕으로 오늘 주가가 변동한 핵심 원인 3줄 요약)
                5. 관련 수혜주 및 테마 체크: (동일한 테마로 묶여 움직이는 관련주 리스트 보고)
                6. 향후 전망 및 인사이트: (수석 분석가 관점에서의 향후 주가 방향성 및 리스크 점검)
                7. 앤트리치의 차트분석: (현재 주가 위치 및 지지/저항선에 대한 기술적 분석 소견 보고)
                8. 3초 결론 박스: (바쁜 상사를 위한 단 한 줄의 최종 결론 및 투자 의견)
                💡 9. 검색 최적화(SEO) 해시태그: (네이버/구글 검색 노출을 극대화할 수 있도록 '{target_stock} 주가', '{target_stock} 전망', 엮인 테마명, 주요 경쟁사 등 트래픽이 높은 핵심 키워드 15~20개를 엄선하여 쉼표로 구분하여 작성)
                """
                
                try:
                    script_response = model.generate_content(script_prompt)
                    st.success(f"✅ [{target_stock}] 심층 분석 보고서 작성이 완료되었습니다!")
                    with st.container(border=True):
                        st.markdown(script_response.text)
                except ResourceExhausted:
                    st.error("🚨 앗! AI 과부하 상태입니다. 딱 1분만 기다리셨다가 다시 버튼을 눌러주세요!")
