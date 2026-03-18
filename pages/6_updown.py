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
                    results.append({"symbol": symbol, "name": name, "change": change_pct})
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
                                    results.append({"symbol": name, "name": name, "change": pct})
                            except:
                                pass
            except:
                continue

    if not results:
        return []
        
    results = sorted(results, key=lambda x: abs(x['change']), reverse=True)[:5]
    
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

if st.session_state.scan_results:
    st.divider()
    st.subheader("🎯 스캔 완료! 어떤 종목을 휴먼 모드로 만들까요?")
    
    options = {}
    for item in st.session_state.scan_results:
        label = f"{item['name']} ({item['symbol']}) / 변동: {item['change']:+.2f}%"
        options[label] = item
        
    selected_label = st.selectbox("종목을 선택하세요:", list(options.keys()))
    selected_stock = options[selected_label]
    
    with st.expander(f"📰 {selected_stock['name']} 관련 수집된 뉴스 보기"):
        st.write(selected_stock['news'])

    if st.button("✍️ 사람 냄새 나는 [데일리 만화 포스팅] 굽기", type="primary", use_container_width=True):
        with st.spinner(f"[{selected_stock['name']}] 휴먼 모드 작가 빙의 중입니다... 👨‍💻"):
            
            # 💡 [핵심] 휴먼 블로거 페르소나를 완벽하게 주입한 강력한 프롬프트!
            prompt = f"""
            당신은 AI가 아닙니다. 당신은 주식 커뮤니티에서 활동하며 2026년까지 자산 1억 달성을 목표로 치열하게 시장과 씨름하는 '앤트리치' 블로그의 실제 주인입니다.
            절대 기계나 AI가 쓴 글처럼 보이지 않도록, 커피 한 잔 마시며 친한 주식 투자 동료에게 썰을 풀듯 아주 자연스럽고 맛깔나는 문장으로 포스팅을 작성해 주세요.
            
            [오늘의 주제 종목]
            - 종목명: {selected_stock['name']} ({selected_stock['symbol']})
            - 변동률: 오늘 하루만 {selected_stock['change']:+.2f}% 움직임
            - 뉴스 팩트: {selected_stock['news']}
            
            [출력 필수 구성]
            1. [블로그 제목]: 검색 유입과 호기심을 동시에 잡는 인간적인 어그로 제목 3가지 추천
            
            2. [블로그 본문 (인사말 + 핫이슈 분석 + 앤트리치 인사이트)]: 
               - 기계적인 요약표나 넘버링(1번, 2번 등)을 쓰지 말고, 자연스러운 문장 형태(단락)로 줄글을 써주세요.
               - 도입부는 "오늘 OO 주주분들 잠 못 이루시겠네요~" 또는 "장 보다가 깜짝 놀랐습니다" 같이 사람 냄새 나게 시작하세요.
               - 주가가 왜 미친 듯이 움직였는지 뉴스를 바탕으로 재미있게 썰을 풀어주세요.
               - 마지막에는 2026년 경제적 자유를 향해 달려가는 앤트리치 관점에서의 대응 전략(추격매수 조심, 관망 등)을 공감 가도록 적어주세요.
               
            3. [데일리 4~6컷 만화 대본]: 개미 캐릭터가 등장하는 스피디한 시황 만화 대본 (대사에 화자 이름 절대 금지, 큰따옴표 안의 대사만 작성할 것)
            
            4. [블로그용 해시태그]: 관련된 해시태그 10개 (쉼표로 구분)
            
            5. [🎨 제미나이 복사/붙여넣기용 이미지 생성 명령어]: 맨 마지막에 아래 텍스트를 정확하게 출력할 것.
               "위 만화 대본을 바탕으로 이미지 4~6장을 생성해 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘. 이미지 안에는 대사가 말풍선 텍스트로 꼭 들어가야 해."

            🚨 [절대 금지어 (AI 냄새 나는 단어들)]
            - "요약하자면", "결론적으로", "이 글에서는", "주의가 필요합니다", "살펴보겠습니다", "기대됩니다" 등 전형적인 AI 문구 절대 사용 금지!
            - 대신 "난리 났네요", "대박입니다", "물리신 분들 힘내시길", "슈팅이 나왔네요", "줍줍" 같은 한국 주식 커뮤니티의 은어를 문맥에 맞게 아주 살짝만 섞어주세요.
            """
            
            try:
                response = model.generate_content(prompt)
                st.success("✅ 진짜 사람이 쓴 것 같은 블로그 포스팅 초안이 완성되었습니다!")
                with st.container(border=True):
                    st.markdown(response.text)
            except ResourceExhausted:
                st.error("🚨 AI 과부하 상태입니다. 딱 1분만 기다렸다가 다시 눌러주세요!")
            except Exception as e:
                st.error(f"🚨 알 수 없는 에러 발생: {e}")
