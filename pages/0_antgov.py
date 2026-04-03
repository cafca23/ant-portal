import streamlit as st
import requests
import google.generativeai as genai
import time
import json
import base64

# ==========================================
# 🔑 0단계: 마스터 키 및 환경 세팅
# ==========================================
GOV_API_KEY = st.secrets["GOV_API_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# 구글 공식 SDK 인증 및 무제한 2.5 엔진 장착!
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 정부 API 주소 (Base64 유지)
GOV_URL = base64.b64decode("aHR0cHM6Ly9hcGkub2RjbG91ZC5rci9hcGkvZ292MjQvdjMvc2VydmljZUxpc3Q=").decode()
GOV_DETAIL_URL = base64.b64decode("aHR0cHM6Ly93d3cuZ292LmtyL3BvcnRhbC9yY3ZmdnJTdmMvZHRsRXgv").decode()

# ==========================================
# 🎨 1단계: 웹사이트 화면 꾸미기
# ==========================================
st.set_page_config(page_title="J.F2.A 정책 번역기", page_icon="🏛️", layout="wide")

st.title("🏛️ J.F2.A 전 세대 맞춤형 블로그 공장")
st.markdown("AI 수석 편집장이 최신 정책을 골라 찰진 글을 쓰고, **1컷씩 분리된 완벽한 만화 주문서**까지 뽑아 드립니다.")

# ==========================================
# ⚙️ 2단계: 핵심 기능 (수집 -> AI 큐레이팅 -> 작문)
# ==========================================

# 💡 고도화 1: 데이터 캐싱 적용 (1시간 동안 정부 서버 재호출 방지 -> 속도 폭발)
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_100_latest_policies():
    params = {"page": 1, "perPage": 100, "serviceKey": GOV_API_KEY}
    try:
        response = requests.get(GOV_URL, params=params, timeout=10)
        if response.status_code != 200:
            return None, f"공공데이터 수집 실패 (에러코드: {response.status_code})"
            
        data = response.json()
        if 'data' not in data or len(data['data']) == 0:
            return None, "가져올 데이터가 없습니다."
            
        policies = []
        for policy in data['data']:
            svc_id = policy.get('서비스ID', policy.get('SVC_ID', ''))
            official_link = f"{GOV_DETAIL_URL}{svc_id}" if svc_id else "정부24 홈페이지 참조"
            
            policies.append({
                "정책명": policy.get('서비스명', policy.get('SVC_NM', '이름 없음')),
                "소관기관": policy.get('소관기관명', policy.get('JRS_GN_NM', '기관 미상')),
                "지원대상": policy.get('지원대상', policy.get('TRG_TER_NM', '내용 없음')),
                "지원내용": policy.get('지원내용', policy.get('SVC_CTS', '내용 없음')),
                "상세주소": official_link
            })
        return policies, None
    except Exception as e:
        return None, f"서버 통신 오류: {e}"

def ai_curator_pick(policies, target_age, count):
    catalog = "\n".join([f"[{i}] {p['정책명']}" for i, p in enumerate(policies)])
    
    prompt = f"""
    당신은 대한민국 최고의 블로그 편집장입니다. 이번 글의 핵심 타겟은 '{target_age}'입니다.
    아래 100개의 정부 정책 중, 이 타겟이 가장 클릭할 만한(돈이 되는) 정책 딱 {count}개만 골라주세요.
    
    [정책 목록]
    {catalog}
    """
    
    # 💡 고도화 2: JSON 배열 형태로만 답변하도록 강제 (오류 원천 차단)
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=list[int]
            )
        )
        numbers = json.loads(response.text)
        return numbers[:count], None
    except Exception as e:
        return None, f"AI 큐레이팅 중 오류 발생: {e}"

def generate_blog_post(policy_info, target_age):
    prompt = f"""
    당신은 경제/정책 블로그 '앤트리치'의 에디터입니다.
    
    [원본 데이터]
    - 정책명: {policy_info['정책명']}
    - 지원대상: {policy_info['지원대상']}
    - 지원내용: {policy_info['지원내용']}
    
    [작성 가이드라인]
    1. 도입부: '{target_age}' 독자가 공감할 현실적인 고민으로 아주 짧게 시작하세요. (상황극 대사 넣지 마세요)
    2. 본문: 어려운 말 빼고, 불릿 포인트(-)로 정책의 핵심 팩트만 요약해 주세요.
    3. 🔥 [핵심] 앤트리치의 진짜 속마음: 본문 요약 후, 검색 노출을 위한 '생활밀착형 검색어'를 자연스럽게 녹이되, 절대 AI가 쓴 느낌이 나지 않게 하세요. '{target_age}' 타겟이 100% 공감할 수 있는 현실적인 한탄, 유머, 인터넷 커뮤니티 말투를 섞어서 아주 찰지고 주관적인 코멘트를 2~3줄 툭 던지듯 작성해 주세요.
    4. 출처/태그: 맨 마지막에 주무부처, 정부24 링크와 해시태그(#) 5개를 적어주세요.
    
    5. ✨ [만화 주문서 통합 작성]: 글 맨 마지막에 별도의 구분선(---)을 긋고, 이미지 AI에 넣을 [🎨 이미지 AI용 만화 주문서]를 한글로 작성해 주세요.
        **[주문서 필수 포함 규칙]**
        - 이미지 생성 AI에게 내릴 첫 번째 지시사항으로 다음 문장을 무조건, 토씨 하나 틀리지 말고 맨 위에 작성하세요: "중요: 만화 이미지를 하나로 합치지 말고, 무조건 1컷당 1개의 이미지 파일로 완벽하게 분리해서 따로따로 생성해 줘."
        - 총 4컷의 스토리를 짜고, 각 컷마다 [장면 묘사]와 타겟이 200% 공감할 [말풍선 대사]를 분리해서 적어주세요.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 블로그 포스팅 작성 중 오류가 발생했습니다: {e}"

# ==========================================
# 🚀 3단계: 화면 조작부 및 실행
# ==========================================
with st.container(border=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        target_age = st.selectbox(
            "🎯 어떤 세대를 타겟으로 글을 쓸까요?",
            ["20대 (대학생, 사회초년생)", 
             "30대 (신혼부부, 영유아 부모)", 
             "40대 (초중고 학부모, 소상공인)", 
             "50대 (중장년, 노후준비)", 
             "60대 이상 (어르신, 요양/건강)"]
        )
    with col2:
        post_count = st.number_input("📝 AI가 몇 개를 골라올까요?", min_value=1, max_value=5, value=1)

if st.button("🚀 AI 편집장, 대박 정책 골라와!", type="primary", use_container_width=True):
    with st.status("AI 수석 편집장이 업무를 시작합니다...", expanded=True) as status:
        st.write("📡 정부24 서버에서 최신 정책 100개를 스캔합니다...")
        policies, error = fetch_100_latest_policies()
        
        if error:
            status.update(label="수집 에러 발생!", state="error")
            st.error(error)
        else:
            st.write(f"🧠 스캔 완료! 제미나이 2.5 엔진이 '{target_age}' 맞춤형 정책을 선별 중입니다...")
            selected_indices, ai_error = ai_curator_pick(policies, target_age, post_count)
            
            if ai_error:
                status.update(label="AI 편집장 분석 실패", state="error")
                st.error(ai_error)
            elif not selected_indices:
                status.update(label="선별 실패", state="error")
                st.error("조건에 맞는 정책을 찾지 못했습니다.")
            else:
                st.write(f"✅ AI 편집장이 {len(selected_indices)}개의 황금 정책을 픽했습니다!")
                
                for i, idx in enumerate(selected_indices):
                    if idx >= len(policies): continue 
                    
                    best_policy = policies[idx]
                    st.write(f"✍️ [{i+1}/{len(selected_indices)}] '{best_policy['정책명']}' 포스팅 & 만화 콘티 작성 중...")
                    
                    blog_content = generate_blog_post(best_policy, target_age)
                    
                    with st.expander(f"✨ AI 편집장의 선택: {best_policy['정책명']}", expanded=True):
                        st.markdown(blog_content)
                        st.caption(f"📍 원본 데이터 확인: {best_policy['상세주소']}")
                    time.sleep(1) # 부하 방지용 딜레이
                
                status.update(label="✅ 오늘의 블로그 원고 및 만화 기획서가 모두 완성되었습니다!", state="complete")
