import streamlit as st
import requests
from datetime import datetime
import time
import re
import base64

# ==========================================
# 🔑 0단계: 마스터 키 영구 고정 (금고에서 꺼내오기)
# ==========================================
GOV_API_KEY = st.secrets["GOV_API_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# 💡 복사 귀신 완벽 방어 암호화 주소
GOV_URL = base64.b64decode("aHR0cHM6Ly9hcGkub2RjbG91ZC5rci9hcGkvZ292MjQvdjMvc2VydmljZUxpc3Q=").decode()
GEMINI_URL = base64.b64decode("aHR0cHM6Ly9nZW5lcmF0aXZlbGFuZ3VhZ2UuZ29vZ2xlYXBpcy5jb20vdjFiZXRhL21vZGVscy9nZW1pbmktMi41LWZsYXNoOmdlbmVyYXRlQ29udGVudA==").decode()
GOV_DETAIL_URL = base64.b64decode("aHR0cHM6Ly93d3cuZ292LmtyL3BvcnRhbC9yY3ZmdnJTdmMvZHRsRXgv").decode()

# ==========================================
# 🎨 1단계: 웹사이트 화면 꾸미기
# ==========================================
st.set_page_config(page_title="J.F2.A 정책 번역기", page_icon="🏛️", layout="wide")

st.title("🏛️ J.F2.A 전 세대 맞춤형 블로그 공장")
st.markdown("AI 편집장이 최신 정책을 골라 글을 쓰고, **말풍선 대사까지 포함된 완벽한 만화 주문서**를 만들어 드립니다.")

# ==========================================
# ⚙️ 2단계: 핵심 기능 (수집 -> AI 편집장 -> AI 작문)
# ==========================================
def fetch_100_latest_policies():
    params = {"page": 1, "perPage": 100, "serviceKey": GOV_API_KEY}
    
    response = requests.get(GOV_URL, params=params)
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

def ai_curator_pick(policies, target_age, count):
    catalog = "\n".join([f"[{i}] {p['정책명']}" for i, p in enumerate(policies)])
    
    prompt = f"""
    당신은 대한민국 최고의 블로그 편집장입니다. 이번 글의 핵심 타겟은 '{target_age}'입니다.
    아래 100개의 정부 정책 중, 이 타겟이 가장 클릭할 만한(돈이 되는) 정책 딱 {count}개만 골라주세요.
    
    [정책 목록]
    {catalog}
    
    [출력 규칙]
    고른 정책의 [번호]만 쉼표로 구분해서 순수 숫자만 출력하세요. (예: 3, 15, 42)
    """
    
    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    for attempt in range(3):
        response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
        
        if response.status_code == 200:
            result_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            numbers = [int(n) for n in re.findall(r'\d+', result_text)]
            return numbers[:count], None
        elif response.status_code == 429:
            return None, "🚨 **[이용량 초과]** 제미나이 AI의 일일 무료 제공량을 모두 사용했습니다. 내일 다시 시도하시거나, 새로운 구글 계정으로 API 키를 발급받아 교체해 주세요!"
        elif response.status_code == 503:
            time.sleep(3)
            continue
        else:
            return None, f"⚠️ AI 연결 중 알 수 없는 문제가 발생했습니다. (에러코드: {response.status_code})"
            
    return None, "⏳ 구글 AI 서버가 현재 너무 바빠서 응답하지 않습니다. 잠시 후 다시 시도해 주세요!"

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
    3. 🔥 [핵심] 앤트리치의 진짜 속마음 (인간미 200% 코멘트): 본문 요약 후, 검색 노출을 위한 '생활밀착형 검색어'를 자연스럽게 녹이되, **절대 AI가 쓴 기계적인 느낌이 나지 않도록 작성하세요.** '{target_age}' 타겟이 100% 공감할 수 있는 현실적인 한탄, 유머, 인터넷 커뮤니티 말투(예: "요즘 물가 미쳤는데 이거라도 꼭 챙깁시다 형님들", "애 키우는 집은 이거 모르면 진짜 손해죠 ㅠㅠ", "내 세금 이렇게라도 돌려받아야죠")를 섞어서 아주 찰지고 주관적인 코멘트를 2~3줄 툭 던지듯 작성해 주세요.
    4. 출처/태그: 맨 마지막에 주무부처, 정부24 링크와 해시태그(#) 5개를 적어주세요.
    5. ✨ [만화 주문서 통합 작성]: 글 완전 맨 마지막에 별도의 구분선(---)을 긋고, 나노바나나 등 이미지 AI에 넣을 [🎨 이미지 AI용 만화 주문서]를 한글로 작성해 주세요.
        
        **[주문서 필수 포함 규칙]**
        - 지시사항 첫 줄에 반드시 다음 문장을 넣으세요: "중요: 만화 이미지를 합치지 말고, 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘."
        - 총 4컷의 스토리를 짜주세요.
        - 각 컷마다 반드시 **[장면 묘사]**와 그림 안에 들어갈 **[말풍선 대사]**를 함께 적어주세요. 대사는 타겟이 100% 공감할 수 있는 아주 현실적인 내용으로 짜주세요.
        
    6. 금지사항: 앞뒤에 ```markdown 기호는 절대 넣지 마세요.
    """
    
    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    for attempt in range(3):
        response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
        
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        elif response.status_code == 429:
            return "🚨 **[작성 중단] 제미나이 AI의 일일 무료 제공량을 모두 사용했습니다.**\n\n오늘은 여기까지! 내일 다시 시도하시거나, 코딩 에디터 첫 줄의 API 키를 새로운 계정의 키로 교체해 주세요."
        elif response.status_code == 503:
            time.sleep(3)
            continue
        else:
            return f"⚠️ AI 번역 실패 (에러코드: {response.status_code})"
            
    return "⏳ 구글 AI 서버가 현재 너무 바빠서 응답하지 않습니다. (503 에러) 잠시 후 다시 시도해 주세요!"

# ==========================================
# 🚀 3단계: 화면 조작부 (세대 선택)
# ==========================================
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

if st.button("🚀 AI 편집장, 대박 정책 골라와!", use_container_width=True):
    with st.status("AI 편집장이 정부 문서를 분석 중입니다...", expanded=True) as status:
        st.write("1. 최신 정책 100개를 수집합니다...")
        policies, error = fetch_100_latest_policies()
        
        if error:
            status.update(label="수집 에러 발생!", state="error")
            st.error(error)
        else:
            st.write(f"2. 수집 완료! 제미나이 편집장이 '{target_age}'에게 좋은 정책을 고르는 중...")
            selected_indices, ai_error = ai_curator_pick(policies, target_age, post_count)
            
            if ai_error:
                status.update(label="AI 편집장 업무 중단", state="error")
                st.warning(ai_error)
            elif not selected_indices:
                status.update(label="선별 실패", state="error")
                st.error("AI가 정책을 고르지 못했습니다. 잠시 후 다시 시도해 주세요.")
            else:
                st.write(f"✅ AI 편집장이 {len(selected_indices)}개의 알짜 정책을 골라냈습니다!")
                
                for i, idx in enumerate(selected_indices):
                    if idx >= len(policies): continue 
                    
                    best_policy = policies[idx]
                    st.write(f"✍️ [{i+1}/{len(selected_indices)}] '{best_policy['정책명']}' 포스팅 및 만화 기획 중...")
                    blog_content = generate_blog_post(best_policy, target_age)
                    
                    with st.expander(f"✨ AI 편집장의 선택: {best_policy['정책명']}", expanded=True):
                        st.markdown(blog_content)
                    time.sleep(1)
                
                status.update(label="오늘의 블로그 포스팅 생산 및 이미지 기획이 완벽하게 끝났습니다!", state="complete")
