import streamlit as st
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_hot_news(market_type):
    hot_news_titles = []
    # 한국 증시 선택 시에만 네이버 API 작동
    if "한국" in market_type:
        try:
            client_id = st.secrets["NAVER_CLIENT_ID"]
            client_secret = st.secrets["NAVER_CLIENT_SECRET"]
            query = urllib.parse.quote("특징주 OR 상한가 OR 수혜주")
            url_naver = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=sim"
            req = urllib.request.Request(url_naver)
            req.add_header("X-Naver-Client-Id", client_id)
            req.add_header("X-Naver-Client-Secret", client_secret)
            res = urllib.request.urlopen(req)
            if res.getcode() == 200:
                data = json.loads(res.read().decode('utf-8'))
                for item in data['items']:
                    clean_title = BeautifulSoup(item['title'], 'html.parser').text
                    hot_news_titles.append(f"[네이버 속보] {clean_title}")
        except: pass

    # 구글 뉴스 수집 (선택된 시장에 따라 키워드 분리)
    try:
        # 💡 [검색어 패치] 미국 증시일 경우, 포괄적 검색어 대신 '실적, 시간외, 특징주' 등 개별 종목 타겟팅으로 변경
        search_keyword = "한국 증시 특징주 OR 코스피 특징주 when:1d" if "한국" in market_type else "미국 주식 (실적 OR 시간외 OR 특징주 OR 급등) when:1d"
        url_google = f"https://news.google.com/rss/search?q={search_keyword}&hl=ko&gl=KR&ceid=KR:ko"
        res_google = requests.get(url_google, headers=headers)
        soup = BeautifulSoup(res_google.text, "xml") # RSS 처리를 위해 xml 파서 사용 권장
        for news in soup.find_all("item")[:15]: 
            hot_news_titles.append(f"[구글 뉴스] {news.title.text}")
    except: pass
    return hot_news_titles

# ==========================================
# --- [1단계] 실시간 핫스탁 검색 ---
# ==========================================
st.header("🔍 1. 실시간 특징주 동향 파악 (🔥 거래량 폭발 연동)")
market = st.radio("어떤 시장을 검색할까요?", ["한국 증시", "미국 증시"], horizontal=True)

if st.button("특징주 동향 검색하기", use_container_width=True):
    with st.spinner("뉴스 및 시장 데이터를 융합 중입니다... 잠시만 기다려주세요! 🚀"):
        hot_news_titles = fetch_hot_news(market)
        
        search_rank_info = ""
        # 한국 증시를 선택했을 때만 네이버 거래량 순위를 추가함
        if "한국" in market:
            rank_str = get_naver_volume_ranks_string()
            if rank_str:
                search_rank_info = f"\n[🔥 금일 코스피 거래량 폭발 상위 종목 (Top 30)]\n{rank_str}\n"

        if not hot_news_titles:
            st.error("🚨 서버 통신 지연. 잠시 후 다시 시도해 주세요!")
        else:
            hot_news_text = "\n".join(hot_news_titles)

            # 💡 [프롬프트 패치] 지수, ETF, 테마 등 뭉뚱그린 표현 절대 금지 & 개별 기업명 강제
            list_prompt = f"""
            당신은 기업의 수석 투자 분석가입니다.
            다음은 수집된 [{market}]의 최근 뉴스 헤드라인과 시장 이슈 데이터입니다.
            
            [최근 뉴스 헤드라인]
            {hot_news_text}
            
            {search_rank_info}
            
            이 데이터들을 완벽하게 분석하여, 현재 시장에서 가장 이슈가 되고 있는 특징주 5개를 도출하여 직장 상사(팀장/본부장)에게 보고하는 형식으로 간결하게 브리핑해 주세요.

            [🚨 작성 규칙 - 매우 중요!]
            1. 도입부는 "본부장님(팀장님), 금일 [{market}] 주요 특징주 동향 보고드립니다."로 시작하세요.
            2. [개별 종목(기업) 최우선 선별 규칙]: 
               - 한국 증시: 제공된 [거래량 폭발 상위 종목] 중에서 뻔한 대형주(KODEX, 삼성전자 등)는 가급적 제외하고, 뉴스가 가장 자극적이고 변동성이 큰 '새로운 특정 기업' 5개를 선별하세요. 종목명 옆에 괄호로 거래량 순위를 반드시 표기하세요.
               - 미국 증시: '나스닥 지수', '에너지 섹터', '레버리지 ETF' 같은 뭉뚱그린 시장 지수나 테마명은 절대 적지 마세요. 뉴스에 등장한 **특정 개별 기업명(예: 테슬라, 애플, 엔비디아, 메타 등)**과 티커 기호(예: TSLA)를 정확히 5개 찾아내어 브리핑하세요. 개별 기업이 아니면 무효입니다.
            3. 종목명과 핵심 상승/하락 사유를 개조식(- 함, - 됨)으로 명확히 기재하세요.
            4. 핵심 팩트 및 종목명을 표시할 때 대괄호([ ])나 꺾쇠(【 】) 같은 특수기호로 감싸지 말고 텍스트만 깔끔하게 작성하세요.
            5. 글 전체에 걸쳐 별표(*) 기호와 이모티콘(이모지)은 단 한 개도 절대 사용하지 마세요.
            6. [줄바꿈 강제]: 가독성을 위해 본문을 작성할 때 문장이 마침표(.)로 끝나면, 무조건 줄바꿈(엔터)을 하여 다음 내용이 새로운 줄에서 시작되도록 하세요.
            """
            
            try:
                list_response = model.generate_content(list_prompt)
                st.success(f"✅ 무제한 엔진 가동! [{market}] 개별 특징주 요약 완료!")
                
                clean_list_text = list_response.text.replace("*", "")
                clean_list_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_list_text)
                
                st.markdown(clean_list_text)
            except Exception as e:
                st.error(f"🚨 알 수 없는 오류가 발생했습니다: {e}")
