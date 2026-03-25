import streamlit as st
import requests
from datetime import datetime
import time
import base64

# ==========================================
# 🔑 마스터 키 (금고에서 꺼내오기)
# ==========================================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GEMINI_URL = base64.b64decode("aHR0cHM6Ly9nZW5lcmF0aXZlbGFuZ3VhZ2UuZ29vZ2xlYXBpcy5jb20vdjFiZXRhL21vZGVscy9nZW1pbmktMi41LWZsYXNoOmdlbmVyYXRlQ29udGVudA==").decode()

# ==========================================
# 🎨 웹사이트 화면 꾸미기
# ==========================================
st.set_page_config(page_title="앤트리치 모닝 브리핑", page_icon="📈", layout="wide")

st.title("📈 앤트리치 모닝 브리핑 공장")
st.markdown("매일 아침 9시 전, **쌍끌이 매수 TOP 5**와 **시간외 급등 TOP 5** 팩트만 모아 완벽한 시황 포스팅을 찍어냅니다.")

# ==========================================
# ⚙️ 1단계: 파이썬 데이터 수집 (크롤링 뼈대)
# ==========================================
# 💡 실제 네이버 금융이나 pykrx 라이브러리를 붙일 수 있는 공간입니다.
# 💡 지금은 AI가 어떻게 글을 쓰는지 확인하기 위해 테스트 데이터를 넣었습니다.
def get_stock_data():
    # 1. 외인/기관 쌍끌이 TOP 5 (테스트 데이터)
    co_buy_top5 = [
        {"종목명": "삼성전자", "특징": "외인/기관 동시 순매수 1위 (반도체 업황 턴어라운드 기대)"},
        {"종목명": "SK하이닉스", "특징": "HBM 수요 폭발, 기관 대량 매수"},
        {"종목명": "현대차", "특징": "역대급 실적 발표 후 외국인 수급 유입"},
        {"종목명": "한미반도체", "특징": "AI 반도체 장비 수주 공시 기대감"},
        {"종목명": "알테오젠", "특징": "바이오주 훈풍, 기관 5거래일 연속 매수"}
    ]
    
    # 2. 시간외 단일가 상승 TOP 5 (테스트 데이터)
    after_hours_top5 = [
        {"종목명": "우진엔텍", "상승률": "+9.8%", "특징": "원전 관련 정부 정책 발표 기대감"},
        {"종목명": "에코프로머티", "상승률": "+8.5%", "특징": "장 마감 후 대규모 공급계약 공시"},
        {"종목명": "제주반도체", "상승률": "+7.2%", "특징": "온디바이스 AI 테마 순환매"},
        {"종목명": "씨씨에스", "상승률": "+6.5%", "특징": "초전도체 관련 이슈 재점화"},
        {"종목명": "흥구석유", "상승률": "+5.1%", "특징": "간밤 국제유가 급등 영향"}
    ]
    
    return co_buy_top5, after_hours_top5

# ==========================================
# ⚙️ 2단계: AI 편집장 브리핑 작성
# ==========================================
def generate_morning_briefing(co_buy, after_hours):
    # 데이터를 예쁜 텍스트로 정리
    co_buy_text = "\n".join([f"- {item['종목명']} ({item['특징']})" for item in co_buy])
    after_hours_text = "\n".join([f"- {item['종목명']} : {item['상승률']} ({item['특징']})" for item in after_hours])
    
    prompt = f"""
    당신은 대한민국 최고의 주식 블로그 '앤트리치'의 수석 에디터입니다.
    오늘 아침 9시 장이 열리기 전, 출근하는 3040 직장인 투자자들을 위해 팩트 기반의 모닝 브리핑을 작성해주세요.
    
    [어제 장 마감 후 수집된 팩트 데이터]
    🔥 외국인/기관 쌍끌이 매수 TOP 5
    {co_buy_text}
    
    🚀 시간외 단일가 급등 TOP 5
    {after_hours_text}
    
    [작성 가이드라인]
    1. 도입부: 활기찬 아침 인사와 함께, 전날 증시의 전반적인 분위기를 2줄로 요약하며 시작하세요.
    2. 본문: '🔥 세력이 찜한 쌍끌이 TOP 5', '🚀 밤사이 터진 시간외 급등 TOP 5'라는 소제목을 달고, 제공된 데이터를 가독성 좋게 불릿 포인트(-)로 정리해주세요.
    3. 💡 앤트리치의 시선 (코멘터리): 이 종목들의 공통점(예: 반도체 주도, 바이오 순환매 등)을 짚어주고, "오늘 장에서는 이 섹터를 주목해보자"는 인사이트를 3줄로 작성해주세요. (단, 특정 종목 무조건 매수 추천은 절대 금지)
    4. ✨ [만화 주문서 통합 작성]: 글 완전 맨 마지막에 별도의 구분선(---)을 긋고, '나노바나나' 등 이미지 AI에 넣을 [🎨 이미지 AI용 만화 주문서]를 작성해 주세요.
       
       **[주문서 필수 포함 규칙]**
       - 첫 줄 지시사항: "중요: 만화 이미지를 합치지 말고, 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘."
       - 오늘 시장 분위기(예: 불장 기대감, 반도체 호황 등)를 담은 4컷 만화 스토리를 짜주세요.
       - 각 컷마다 **[장면 묘사]**와 3040 개미 투자자가 공감할 **[말풍선 대사]**를 함께 적어주세요.
       
    5. 금지사항: 앞뒤에 ```markdown 기호는 절대 넣지 마세요.
    """
    
    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    for attempt in range(3):
        response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
        
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text'], None
        elif response.status_code == 429:
            return None, "🚨 **[이용량 초과]** 제미나이 AI 일일 무료 제공량을 모두 사용했습니다."
        elif response.status_code == 503:
            time.sleep(3)
            continue
        else:
            return None, f"⚠️ AI 연결 중 문제가 발생했습니다. (에러코드: {response.status_code})"
            
    return None, "⏳ 구글 AI 서버 응답 지연. 잠시 후 다시 시도해 주세요!"

# ==========================================
# 🚀 3단계: 화면 조작부
# ==========================================
st.markdown("### 📊 오늘의 팩트 데이터 추출하기")
if st.button("🚀 앤트리치 모닝 브리핑 포스팅 생성!", use_container_width=True):
    with st.status("데이터를 수집하고 브리핑을 작성 중입니다...", expanded=True) as status:
        st.write("1. 어제자 쌍끌이 및 시간외 TOP 5 데이터를 수집합니다...")
        co_buy, after_hours = get_stock_data()
        time.sleep(1) # 크롤링 하는 척 대기
        
        st.write("2. AI 에디터가 출근길 맞춤형 시황 분석 글을 작성 중입니다...")
        blog_content, ai_error = generate_morning_briefing(co_buy, after_hours)
        
        if ai_error:
            status.update(label="브리핑 작성 실패", state="error")
            st.warning(ai_error)
        else:
            st.write("✅ 앤트리치 모닝 브리핑 작성이 완료되었습니다!")
            st.markdown("---")
            st.markdown(blog_content)
            
            status.update(label="오늘의 모닝 브리핑 및 만화 기획 완료!", state="complete")
