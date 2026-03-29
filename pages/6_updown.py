import streamlit as st
import urllib.request
import urllib.parse
import json
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import warnings
import re

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# ==========================================
# 0. AI 및 텔레그램 세팅
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# 💡 텔레그램 암호키 불러오기 (secrets.toml에 이미 세팅됨)
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

st.set_page_config(page_title="앤트리치 급등락 스캐너", page_icon="🎢")

st.title("🎢 데일리 급등락 스캐너 & 심층 보고서")
st.write("10% 이상 움직인 종목을 스캔하고, 직장 상사에게 보고하는 형태의 각 잡힌 종목 분석 보고서를 즉시 생성하여 텔레그램으로 쏩니다.")
st.divider()

# 💡 텔레그램으로 메시지를 쏘는 핵심 배관 함수 추가
def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    
    try:
        res = requests.post(url, json=payload)
        return res.status_code == 200
    except:
        return False

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
    
    options = {}
    for item in st.session_state.scan_results:
        label = f"{item['name']} / 변동: {item['change']:+.2f}%"
        options[label] = item
        
    selected_label = st.selectbox("스캔된 종목 (참고용):", list(options.keys()))
    selected_stock = options[selected_label]

    st.markdown("👇 **검색할 종목 이름을 확인하거나 직접 입력하세요!**")
    target_stock = st.text_input("종목명 입력:", value=selected_stock['name'])

    if st.button("✍️ [급등락 심층 보고서] 출력 & 텔레그램 발송", type="primary", use_container_width=True):
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

                # 💡 [프롬프트 수정] 가독성 줄바꿈 강제 및 텔레그램/블로그 유도 멘트 추가
                prompt = f"""
                당신은 기업의 수석 투자 분석가입니다.
                다음은 오늘 시장에서 급등/급락한 [{clean_symbol}] 주식에 대해 실시간으로 수집된 최신 뉴스 데이터입니다.
                
                {news_text}

                이 데이터를 완벽하게 종합 분석해서, 직장 상사(팀장/본부장)에게 보고하는 형식의 심층 분석 보고서를 작성해 주세요.

                [🚨 매우 중요한 작성 규칙 및 양식]
                1. 도입부: 반드시 "본부장님(또는 팀장님), [{clean_symbol}] 금일 주가 급변동 핵심 요인 보고드립니다." 로 시작하세요.
                2. [가독성 강제]: ■ 기호가 붙은 제목을 작성한 후에는 반드시 엔터(Enter)를 쳐서 다음 줄에서 내용을 시작하세요.
                3. [어투 종결 강제]: 1번~4번 항목까지의 문장 끝에 절대 "~습니다", "~입니다", "~해요"를 사용하지 마세요. 무조건 "~함", "~됨", "~했음", "~예상됨", "~필요함" 형식으로 철저하게 끊어지는 명사형 개조식으로만 작성하세요. 
                4. [기호 사용 완전 통제]: 글 전체에 걸쳐서 별표 기호와 이모티콘(이모지)은 단 한 개도 절대 사용하지 마세요. 강조할 때는 대괄호([ ])나 꺾쇠(【 】)를 사용하세요.
                
                [출력 필수 구성 (순서대로 정확히 출력할 것)]
                ■ 1. 추천 보고서(블로그) 제목 2가지
                (반드시 줄바꿈 후 작성)

                ■ 2. [{clean_symbol}] 기업 소개 (3줄 요약)
                (반드시 줄바꿈 후 작성) 핵심 비즈니스 모델 요약. 반드시 ~함, ~기업임 으로 끝낼 것.

                ■ 3. [{clean_symbol}] 주가 변동 원인 분석
                (반드시 줄바꿈 후 작성) 뉴스 기반 팩트 분석. 반드시 ~함, ~됨 으로 끝낼 것.
                
                ■ 4. 애널리스트 종합 의견 및 향후 전망
                (반드시 줄바꿈 후 작성) 전문가적 견해 요약. 반드시 ~예상됨, ~필요함 등으로 끝낼 것.
                
                ■ 5. 🔥 앤트리치의 찐 속마음 (인간미 코멘트)
                (반드시 줄바꿈 후 작성) 3040 직장인 개미 투자자에게 빙의해 아주 찰지고 주관적인 코멘트를 2~3줄 작성.

                ■ 6. 블로그 확인 링크 안내
                (반드시 줄바꿈 후 작성) 아래 문장을 그대로 똑같이 출력하세요:
                "👉 자세한 차트 대응 전략과 4컷 만화는 앤트리치 블로그 본문에서 확인하세요!"
                (블로그 링크: https://대표님의블로그주소.com)

                ■ 7. [붙임] 마케팅용 웹툰 스토리보드 기획안 (4~6컷)
                (반드시 줄바꿈 후 작성) 주식 투자하는 개미(Ant) 캐릭터가 주인공으로 등장하는 대본.
                
                ■ 8. [🎨 이미지 생성 명령어]
                (반드시 줄바꿈 후 작성) "위 만화 대본을 바탕으로 이미지 4~6장을 생성해 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘. 그리고 반드시 각 이미지 안의 말풍선에 해당 컷의 대사를 텍스트로 넣어줘."
                
                ■ 9. 블로그용 해시태그
                (반드시 줄바꿈 후 작성) 쉼표로 구분된 관련 키워드 10개.
                """
                
                try:
                    script_response = model.generate_content(prompt)
                    
                    clean_result_text = script_response.text.replace('*', '')
                    clean_result_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_result_text)
                    
                    st.success(f"✅ [{clean_symbol}] 분석 보고서 작성이 완료되었습니다!")
                    with st.container(border=True):
                        st.markdown(clean_result_text)
                        
                    # 💡 텔레그램 발사 로직!
                    with st.spinner("📲 텔레그램 채널로 마감 시황을 전송하는 중..."):
                        if send_telegram_message(clean_result_text):
                            st.success("🎉 텔레그램 채널에 데일리 급등락 보고서가 성공적으로 발송되었습니다!")
                        else:
                            st.error("🚨 텔레그램 전송 실패. secrets.toml의 토큰과 채널 아이디를 확인해 주세요.")
                            
                except ResourceExhausted:
                    st.error("🚨 AI 과부하 상태입니다. 딱 1분만 기다리셨다가 다시 눌러주세요!")
                except Exception as e:
                    st.error(f"🚨 알 수 없는 오류 발생: {e}")
