import streamlit as st
import urllib.request
import urllib.parse
import json
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# ==========================================
# 0. AI 세팅
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

st.set_page_config(page_title="앤트리치 급등락 스캐너", page_icon="🎢")

st.title("🎢 데일리 급등락 스캐너 & 심층 보고서")
st.write("10% 이상 움직인 종목을 스캔하고, 직장 상사에게 보고하는 형태의 각 잡힌 종목 분석 보고서를 즉시 생성합니다.")
st.divider()

if "scan_results" not in st.session_state:
    st.session_state.scan_results = []
if "market_type" not in st.session_state:
    st.session_state.market_type = "🇺🇸 미국 증시"

st.session_state.market_type = st.radio("어느 시장을 스캔할까요?", ["🇺🇸 미국 증시", "🇰🇷 한국 증시"], horizontal=True)

@st.cache_data(ttl=600, show_spinner=False)
def run_scanner(market, mover_type="gainers"):
    results = []
    
    if "미국" in market:
        url = f"https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&lang=en-US&region=US&scrIds=day_{mover_type}&count=30"
        try:
            req = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(req)
            data = json.loads(response.read().decode('utf-8'))
            quotes = data['finance']['result'][0]['quotes']
            for stock in quotes:
                symbol = stock.get('symbol', '')
                name = stock.get('shortName', symbol)
                change_pct = stock.get('regularMarketChangePercent', 0)
                if (mover_type == "gainers" and change_pct >= 10.0) or (mover_type == "losers" and change_pct <= -10.0):
                    results.append({"symbol": symbol, "name": name, "change": change_pct, "is_us": True})
        except:
            pass
            
    else:
        page_type = "rise" if mover_type == "gainers" else "fall"
        urls = [
            f"https://finance.naver.com/sise/sise_{page_type}.naver?sosok=0",
            f"https://finance.naver.com/sise/sise_{page_type}.naver?sosok=1"
        ]
        for url in urls:
            try:
                res = requests.get(url, headers=headers)
                soup = BeautifulSoup(res.text, 'html.parser')
                rows = soup.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5: 
                        name_tag = cols[1].find('a')
                        if name_tag:
                            name = name_tag.text.strip()
                            pct_text = cols[4].text.strip().replace('%', '').replace(',', '').replace('+', '')
                            try:
                                pct = float(pct_text)
                                if (mover_type == "gainers" and pct >= 10.0) or (mover_type == "losers" and pct <= -10.0):
                                    results.append({"symbol": name, "name": name, "change": pct, "is_us": False})
                            except:
                                pass
            except:
                continue

    if not results:
        return []
        
    return sorted(results, key=lambda x: abs(x['change']), reverse=True)[:5]

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 10% 이상 폭등주 스캔", use_container_width=True):
        with st.spinner("야후/네이버 금융 스캔 중..."):
            st.session_state.scan_results = run_scanner(st.session_state.market_type, "gainers")
            if not st.session_state.scan_results:
                st.info("조건에 맞는 종목이 없습니다.")
with col2:
    if st.button("🩸 10% 이상 폭락주 스캔", use_container_width=True):
        with st.spinner("야후/네이버 금융 스캔 중..."):
            st.session_state.scan_results = run_scanner(st.session_state.market_type, "losers")
            if not st.session_state.scan_results:
                st.info("조건에 맞는 종목이 없습니다.")

if st.session_state.scan_results:
    st.divider()
    st.subheader("🎯 스캔 완료! 어떤 종목을 분석 보고서로 만들까요?")
    
    # 1. 참고용 드롭다운
    options = {}
    for item in st.session_state.scan_results:
        label = f"{item['name']} / 변동: {item['change']:+.2f}%"
        options[label] = item
        
    selected_label = st.selectbox("스캔된 종목 (참고용):", list(options.keys()))
    selected_stock = options[selected_label]

    # 2. 직접 입력/수정 가능한 텍스트 창
    st.markdown("👇 **검색할 종목 이름을 확인하거나 직접 입력하세요!**")
    target_stock = st.text_input("종목명 입력:", value=selected_stock['name'])

    if st.button("✍️ [급등락 심층 보고서] 출력", type="primary", use_container_width=True):
        if not target_stock:
            st.warning("종목 이름을 입력해 주세요!")
        else:
            with st.spinner(f"[{target_stock}] 변동 요인 데이터 취합 및 공식 보고서 작성 중... 👨‍💻"):
                
                target_news_titles = []
                clean_symbol = target_stock.strip()
                
                if "미국" in st.session_state.market_type:
                    news_url = f"https://news.google.com/rss/search?q={clean_symbol}+stock+news+when:1d&hl=en-US&gl=US&ceid=US:en"
                    try:
                        res = requests.get(news_url, headers=headers)
                        soup = BeautifulSoup(res.text, "html.parser")
                        for news in soup.find_all("item")[:10]:
                            target_news_titles.append(f"[구글] {news.title.text}")
                    except: pass
                else:
                    try:
                        client_id = st.secrets["NAVER_CLIENT_ID"]
                        client_secret = st.secrets["NAVER_CLIENT_SECRET"]
                        
                        query = urllib.parse.quote(f"{clean_symbol} 주식 OR 특징주")
                        url_naver = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=sim"
                        
                        req = urllib.request.Request(url_naver)
                        req.add_header("X-Naver-Client-Id", client_id)
                        req.add_header("X-Naver-Client-Secret", client_secret)
                        res = urllib.request.urlopen(req)
                        
                        if res.getcode() == 200:
                            data = json.loads(res.read().decode('utf-8'))
                            for item in data['items']:
                                clean_title = BeautifulSoup(item['title'], 'html.parser').text
                                clean_desc = BeautifulSoup(item['description'], 'html.parser').text
                                target_news_titles.append(f"[네이버] 제목: {clean_title} / 요약: {clean_desc}")
                    except Exception as e: 
                        st.error(f"네이버 뉴스 수집 중 에러 발생: {e}")
                        
                    try:
                        url_google = f"https://news.google.com/rss/search?q={clean_symbol} 주식 when:1d&hl=ko&gl=KR&ceid=KR:ko"
                        res_google = requests.get(url_google, headers=headers)
                        soup_google = BeautifulSoup(res_google.text, "html.parser")
                        for news in soup_google.find_all("item")[:10]:
                            target_news_titles.append(f"[구글] {news.title.text}")
                    except: pass

                news_text = "\n".join(target_news_titles) if target_news_titles else "최근 특별한 뉴스가 없습니다."
                
                with st.expander(f"📰 '{clean_symbol}' 수집 뉴스 확인"):
                    st.write(news_text)

                # 💡 [핵심] 직장 상사 보고용으로 완벽 개조된 프롬프트
                prompt = f"""
                당신은 기업의 수석 투자 분석가입니다.
                다음은 오늘 시장에서 급등/급락한 [{clean_symbol}] 주식에 대해 실시간으로 수집된 최신 뉴스 데이터입니다.
                
                {news_text}

                이 데이터를 완벽하게 종합 분석해서, 직장 상사(팀장/본부장)에게 보고하는 형식의 심층 분석 보고서를 작성해 주세요.

                [🚨 매우 중요한 작성 규칙 및 양식]
                1. 도입부: 반드시 "본부장님(또는 팀장님), [{clean_symbol}] 금일 주가 급변동 핵심 요인 보고드립니다." 로 시작하세요.
                2. 개조식 보고: 감정적인 서론 없이 바로 섹션을 나누어 개조식(~함, ~됨, ~전망)으로 간결하게 보고하세요.
                3. 팩트 강조: 주가 변동의 핵심 원인, 주요 수치, 관련 기업명 등 보고의 팩트는 반드시 **굵은 글씨(마크다운)**로 강조하세요.
                
                [출력 필수 구성]
                ■ 1. [{clean_symbol}] 주가 변동 원인 분석
                - (수집된 뉴스를 바탕으로 왜 급변동했는지 명확한 팩트 위주로 3~4줄 요약 보고)
                
                ■ 2. 애널리스트 종합 의견 및 향후 전망
                - (단기적인 노이즈인지, 펀더멘털의 구조적 변화인지 전문가적 견해 요약)
                
                ■ 3. [붙임] 마케팅용 웹툰 스토리보드 기획안 (4~6컷)
                - (해당 이슈를 대중에게 쉽게 알리기 위한 4~6컷 웹툰 대본 기획. 각 컷별 이미지 생성 지시문과 대사 필수. 대사는 반드시 이미지 안에 말풍선 텍스트로 포함되도록 지시할 것.)
                
                ■ 4. 블로그용 해시태그: (쉼표로 구분된 관련 키워드 10개)
                
                ■ 5. [🎨 이미지 생성 명령어]: 포스팅 맨 마지막에 아래 텍스트를 정확하게 출력할 것.
                "위 만화 대본을 바탕으로 이미지 4~6장을 생성해 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘."
                """
                
                try:
                    response = model.generate_content(prompt)
                    st.success(f"✅ [{clean_symbol}] 분석 보고서 작성이 완료되었습니다!")
                    with st.container(border=True):
                        st.markdown(response.text)
                except ResourceExhausted:
                    st.error("🚨 AI 과부하 상태입니다. 딱 1분만 기다렸다가 다시 눌러주세요!")
