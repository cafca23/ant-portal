import streamlit as st
import urllib.request
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

st.title("🎢 데일리 급등락 스캐너 & 만화 공장")
st.write("10% 이상 움직인 종목을 스캔하고, 클릭 한 번으로 '데일리 4~6컷 만화 포스팅'을 구워냅니다.")
st.divider()

# ==========================================
# 세션 상태 초기화 (데이터 저장용)
# ==========================================
if "scan_results" not in st.session_state:
    st.session_state.scan_results = []
if "market_type" not in st.session_state:
    st.session_state.market_type = "🇺🇸 미국 증시"

# ==========================================
# 1. 시장 선택 옵션
# ==========================================
st.session_state.market_type = st.radio("어느 시장을 스캔할까요?", ["🇺🇸 미국 증시", "🇰🇷 한국 증시"], horizontal=True)

# ==========================================
# 2. 스캐너 엔진
# ==========================================
def run_scanner(market, mover_type="gainers"):
    results = []
    
    # 🇺🇸 미국 증시
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
                    results.append({"symbol": symbol, "name": name, "change": change_pct})
        except:
            return []
            
    # 🇰🇷 한국 증시
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
                                    results.append({"symbol": name, "name": name, "change": pct})
                            except:
                                pass
            except:
                continue

    if not results:
        return []
        
    results = sorted(results, key=lambda x: abs(x['change']), reverse=True)[:5]
    
    # 뉴스 스캔 추가
    for stock in results:
        symbol = stock['symbol']
        news_headlines = []
        if "미국" in market:
            news_url = f"https://news.google.com/rss/search?q={symbol}+stock+news+when:1d&hl=en-US&gl=US&ceid=US:en"
            try:
                res = requests.get(news_url, headers=headers)
                soup = BeautifulSoup(res.text, "html.parser")
                for news in soup.find_all("item")[:3]:
                    news_headlines.append(news.title.text)
            except:
                pass
        else:
            try:
                client_id = st.secrets["NAVER_CLIENT_ID"]
                client_secret = st.secrets["NAVER_CLIENT_SECRET"]
                query = urllib.parse.quote(f"{symbol} 특징주 OR 상한가 OR 하한가")
                url_naver = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=3&sort=sim"
                req = urllib.request.Request(url_naver)
                req.add_header("X-Naver-Client-Id", client_id)
                req.add_header("X-Naver-Client-Secret", client_secret)
                res = urllib.request.urlopen(req)
                if res.getcode() == 200:
                    data = json.loads(res.read().decode('utf-8'))
                    for item in data['items']:
                        clean_title = BeautifulSoup(item['title'], 'html.parser').text
                        news_headlines.append(clean_title)
            except:
                pass
        stock['news'] = "\n".join(news_headlines) if news_headlines else "특별한 뉴스가 없습니다."
        
    return results

# ==========================================
# 3. 스캔 버튼 영역
# ==========================================
col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 10% 이상 폭등주 스캔", use_container_width=True):
        with st.spinner("스캔 중..."):
            st.session_state.scan_results = run_scanner(st.session_state.market_type, "gainers")
            if not st.session_state.scan_results:
                st.info("조건에 맞는 종목이 없습니다.")
with col2:
    if st.button("🩸 10% 이상 폭락주 스캔", use_container_width=True):
        with st.spinner("스캔 중..."):
            st.session_state.scan_results = run_scanner(st.session_state.market_type, "losers")
            if not st.session_state.scan_results:
                st.info("조건에 맞는 종목이 없습니다.")

# ==========================================
# 4. 💡 [신규] 스캔 결과 확인 및 만화 생성 구역
# ==========================================
if st.session_state.scan_results:
    st.divider()
    st.subheader("🎯 스캔 완료! 어떤 종목을 만화로 만들까요?")
    
    # 선택지 만들기
    options = {}
    for item in st.session_state.scan_results:
        label = f"{item['name']} ({item['symbol']}) / 변동: {item['change']:+.2f}%"
        options[label] = item
        
    selected_label = st.selectbox("종목을 선택하세요:", list(options.keys()))
    selected_stock = options[selected_label]
    
    # 선택된 종목의 뉴스 미리보기
    with st.expander(f"📰 {selected_stock['name']} 관련 수집된 뉴스 보기"):
        st.write(selected_stock['news'])

    if st.button("✍️ 이 종목으로 [데일리 4~6컷 만화] 포스팅 굽기", type="primary", use_container_width=True):
        with st.spinner(f"[{selected_stock['name']}]의 뉴스를 분석하여 만화 대본을 작성 중입니다... 👨‍🎨"):
            
            prompt = f"""
            당신은 '앤트리치' 주식 블로그의 수석 작가입니다.
            선택된 종목 [{selected_stock['name']} ({selected_stock['symbol']})]이 오늘 {selected_stock['change']:+.2f}% 변동했습니다.
            다음은 관련된 수집 뉴스입니다:
            {selected_stock['news']}
            
            이 내용을 바탕으로 블로그의 '데일리 급등락 뉴스' 카테고리에 올릴 완벽한 포스팅 초안을 작성해 주세요.
            
            [출력 필수 구성]
            1. [블로그 제목 추천]: 클릭을 유도하는 매력적인 제목 3가지
            2. [오늘의 핫이슈 3줄 요약]: 주가 변동의 핵심 이유
            3. [데일리 4~6컷 만화 대본]: 개미 캐릭터가 등장하는 시황 만화 대본
            4. [앤트리치 인사이트]: 이 종목에 대한 향후 전망이나 투자 시 주의점
            5. [블로그용 해시태그]: 관련된 해시태그 10개 (쉼표로 구분)
            6. [🎨 제미나이 복사/붙여넣기용 이미지 생성 명령어]: 포스팅 맨 마지막에 아래 텍스트를 정확하게 출력할 것.
               "위 만화 대본을 바탕으로 이미지 4~6장을 생성해 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘. 이미지 안에는 대사가 말풍선 텍스트로 꼭 들어가야 해."

            🚨 [매우 중요한 작성 규칙 - 만화 대본]
            - 반드시 4컷에서 6컷 사이로 스피디하게 구성하세요.
            - 만화 대본을 작성할 때, 대사 부분에는 '(개미 1)', '(투자자)' 같은 화자 이름을 절대 적지 말고, 오직 말하는 내용만 큰따옴표 안에 적으세요. 
              (❌ 잘못된 예시: 대사: (개미 1) "와, 상한가다!")
              (⭕ 올바른 예시: 대사: "와, 상한가다!")
            """
            
            try:
                response = model.generate_content(prompt)
                st.success("✅ 만화 포스팅 초안이 완성되었습니다! 복사해서 블로그에 올리고 이미지를 뽑아보세요!")
                with st.container(border=True):
                    st.markdown(response.text)
            except ResourceEx
