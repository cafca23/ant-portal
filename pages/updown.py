import streamlit as st
import urllib.request
import json
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# ==========================================
# 0. AI 세팅
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

st.set_page_config(page_title="앤트리치 급등락 스캐너", page_icon="🎢")

st.title("🎢 한/미 증시 10% 급등락 스캐너")
st.write("미장과 국장에서 10% 이상 미친 듯이 움직인 종목들을 찾아내고, 뉴스를 뒤져 그 이유를 즉시 분석합니다.")
st.divider()

# ==========================================
# 1. 시장 선택 옵션
# ==========================================
target_market = st.radio("어느 시장을 스캔할까요?", ["🇺🇸 미국 증시", "🇰🇷 한국 증시"], horizontal=True)

# ==========================================
# 2. 스캐너 엔진 (미국: 야후 / 한국: 네이버 금융)
# ==========================================
@st.cache_data(ttl=1800, show_spinner=False)
def get_extreme_movers(market, mover_type="gainers"):
    results = []
    
    # ----------------------------------------
    # 🇺🇸 미국 증시 (야후 파이낸스)
    # ----------------------------------------
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
                
                if mover_type == "gainers" and change_pct >= 10.0:
                    results.append({"symbol": symbol, "name": name, "change": change_pct})
                elif mover_type == "losers" and change_pct <= -10.0:
                    results.append({"symbol": symbol, "name": name, "change": change_pct})
        except:
            return "미국 데이터 로드 실패"
            
    # ----------------------------------------
    # 🇰🇷 한국 증시 (네이버 금융 스크래핑)
    # ----------------------------------------
    else:
        # 0: 코스피, 1: 코스닥
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
                            # 5번째 열에 있는 등락률(%) 데이터 추출
                            pct_text = cols[4].text.strip().replace('%', '').replace(',', '').replace('+', '')
                            try:
                                pct = float(pct_text)
                                if mover_type == "gainers" and pct >= 10.0:
                                    results.append({"symbol": name, "name": name, "change": pct})
                                elif mover_type == "losers" and pct <= -10.0:
                                    results.append({"symbol": name, "name": name, "change": pct})
                            except:
                                pass
            except:
                continue

    # 조건에 맞는 종목이 없으면 종료
    if not results:
        return "조건(±10%)에 맞는 종목이 없습니다. 잔잔한 장이네요!"
        
    # 등락률이 가장 큰 순서대로 정렬 후 상위 5개만 컷팅!
    results = sorted(results, key=lambda x: abs(x['change']), reverse=True)[:5]
    final_text = []
    
    # ----------------------------------------
    # 3. AI 뉴스 요약 (미국: 구글 / 한국: 네이버 API)
    # ----------------------------------------
    for stock in results:
        symbol = stock['symbol']
        change_str = f"+{stock['change']:.2f}%" if stock['change'] > 0 else f"{stock['change']:.2f}%"
        news_headlines = []
        
        # 미국은 구글 뉴스 영문 스캔
        if "미국" in market:
            news_url = f"https://news.google.com/rss/search?q={symbol}+stock+news+when:1d&hl=en-US&gl=US&ceid=US:en"
            try:
                res = requests.get(news_url, headers=headers)
                soup = BeautifulSoup(res.text, "html.parser")
                for news in soup.find_all("item")[:3]:
                    news_headlines.append(news.title.text)
            except:
                pass
                
        # 한국은 네이버 API로 한글 특징주 스캔 (더 빠르고 정확함)
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

        news_context = "\n".join(news_headlines) if news_headlines else "최근 24시간 특별한 뉴스가 없습니다."
        
        # AI 요약 지시
        prompt = f"""
        주식 [{symbol}]가 오늘 {change_str} 변동했습니다.
        다음 뉴스 헤드라인들을 보고, 주가 변동의 핵심 이유를 한국어로 딱 1줄로 요약해 주세요.
        쓸데없는 인사말 없이 이유만 바로 적으세요. (이유를 모르면 '명확한 뉴스 없음'이라고 적으세요)
        뉴스:
        {news_context}
        """
        
        try:
            ai_reason = model.generate_content(prompt).text.strip()
        except:
            ai_reason = "이유 분석 실패"
            
        emoji = "🚀" if stock['change'] > 0 else "🩸"
        
        if "미국" in market:
            final_text.append(f"### {emoji} {stock['name']} ({symbol}) : **{change_str}**\n- **원인:** {ai_reason}\n")
        else:
            final_text.append(f"### {emoji} {stock['name']} : **{change_str}**\n- **원인:** {ai_reason}\n")
            
    return "\n".join(final_text)

# ==========================================
# 4. 메인 실행 버튼
# ==========================================
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 10% 이상 폭등주 찾기", use_container_width=True):
        with st.spinner(f"{target_market}에서 폭등주를 스캔하고 찌라시를 분석 중입니다... 🕵️‍♂️ (약 10초)"):
            result = get_extreme_movers(target_market, "gainers")
            st.success("스캔 완료!")
            with st.container(border=True):
                st.markdown(result)

with col2:
    if st.button("🩸 10% 이상 폭락주 찾기", use_container_width=True):
        with st.spinner(f"{target_market}에서 폭락주를 스캔하고 악재를 분석 중입니다... 🕵️‍♂️ (약 10초)"):
            result = get_extreme_movers(target_market, "losers")
            st.success("스캔 완료!")
            with st.container(border=True):
                st.markdown(result)