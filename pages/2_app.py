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
st.title("🐜 앤트리치 종목 분석 자동화 봇")
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

            # 💡 [핵심] 1단계 보고용 프롬프트
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
                # 🧠 [핵심] 100% 직장상사 보고용으로 개조된 프롬프트!
                # ==========================================
                script_prompt = f"""
                당신은 기업의 수석 투자 분석가이자 콘텐츠 기획자입니다.
                다음 수집된 '{target_stock}' 관련 최신 뉴스를 바탕으로, 직장 상사(본부장/팀장)에게 보고하는 형태의 '종목 심층 분석 보고서'를 작성해 주세요. 

                [수집된 데이터]
                {target_news_text}
                
                [🚨 매우 중요한 작성 규칙 및 양식]
                1. [어투와 톤앤매너]: 철저하게 직장 상사에게 보고하는 비즈니스 포맷으로 작성하세요. (예: "본부장님, {target_stock} 핵심 이슈 및 대응 전략 보고드립니다.") 감정적 표현을 배제하고 매우 객관적이고 간결하게 작성하세요.
                2. [팩트 강조]: 주요 수치, 핵심 원인, 종목명 등 보고의 핵심 팩트는 반드시 **굵은 글씨(마크다운)**로 처리하여 가독성을 높이세요.
                3. [개조식 활용]: 줄글보다는 기호(-, *)를 활용한 개조식 포맷팅(~함, ~됨, ~전망)을 사용하여 내용을 구조화하세요.
                
                [출력 필수 구성]
                1. [보고서 제목]: 공식 보고서 형태의 제목 (예: [이슈보고] {target_stock} 주가 변동 원인 분석 및 향후 전망)
                2. [현황 브리핑]: 현재 해당 종목의 핵심 이슈와 시장 반응을 2~3줄로 요약 보고.
                3. [이슈 상세 분석]: 뉴스를 바탕으로 상승/하락을 견인한 근본적인 팩트 체크 및 수혜/피해 현황 분석.
                4. [투자의견 및 대응 전략]: 전문 애널리스트 관점에서의 향후 전망 및 포트폴리오 대응(매수/매도/관망 등) 전략 보고.
                5. [붙임: 마케팅용 웹툰 스토리보드 기획안]: 이 보고서 내용을 대중에게 쉽게 알리기 위한 10컷 웹툰 기획안. (각 컷별 이미지 생성 지시문과 대사 필수. 지시문에는 반드시 해당 컷의 대사가 이미지 안에 말풍선 텍스트로 포함되도록 영어로 명령할 것.)
                6. [블로그용 해시태그]: 콘텐츠 확산을 위한 해시태그 20개 (쉼표로 구분)
                7. [🎨 이미지 생성 명령어]: 포스팅 맨 마지막에 아래 텍스트를 정확하게 출력할 것.
                   "위 만화 대본을 바탕으로 이미지 10장을 생성해 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘."
                """
                
                try:
                    script_response = model.generate_content(script_prompt)
                    st.success(f"✅ [{target_stock}] 심층 분석 보고서 작성이 완료되었습니다!")
                    with st.container(border=True):
                        st.markdown(script_response.text)
                except ResourceExhausted:
                    st.error("🚨 앗! AI 과부하 상태입니다. 딱 1분만 기다리셨다가 다시 버튼을 눌러주세요!")
