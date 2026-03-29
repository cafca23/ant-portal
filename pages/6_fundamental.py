import streamlit as st
import requests
from datetime import datetime, timedelta
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import re

# ==========================================
# 0. API 세팅 및 암호키 불러오기
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')
DART_API_KEY = st.secrets["DART_API_KEY"]

st.set_page_config(page_title="앤트리치 펀더멘털 스캐너", page_icon="🏢", layout="wide")

st.title("🏢 앤트리치 펀더멘털(공시) 스캐너")
st.write("돈이 되는 핵심 공시(유상증자, 수주계약 등)만 필터링하여, 개미들이 환장할 팩트 체크 보고서를 즉시 뽑아냅니다.")
st.divider()

# ==========================================
# 1. DART 공시 데이터 수집 엔진
# ==========================================
def get_hot_dart_reports():
    # 주말 방어: 최근 3일로 기간을 넉넉하게 잡습니다.
    today = datetime.today()
    past_day = today - timedelta(days=3) 
    bgn_de = past_day.strftime("%Y%m%d")
    end_de = today.strftime("%Y%m%d")
    
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "page_count": 100
    }
    
    try:
        res = requests.get(url, params=params)
        data = res.json()
        
        # 013 에러 세탁: 조회된 데이터가 없는 건 에러가 아닙니다.
        if data.get("status") == "013":
            return [], None
        elif data.get("status") != "000":
            return None, f"DART 데이터 수집 실패 (상태코드: {data.get('status')})"
            
        reports = data.get("list", [])
        
        # 돈 되는 핫 키워드 필터링
        hot_keywords = ["유상증자", "무상증자", "단일판매", "공급계약", "자기주식", "영업잠정실적"]
        filtered_reports = []
        
        for r in reports:
            title = r.get("report_nm", "")
            if any(keyword in title for keyword in hot_keywords):
                filtered_reports.append({
                    "회사명": r.get("corp_nm", ""),
                    "공시제목": title,
                    "제출인": r.get("flr_nm", ""),
                    "접수일자": r.get("rcept_dt", "")
                })
                
        return filtered_reports[:5], None 
    except Exception as e:
        return None, f"서버 통신 에러: {e}"

# ==========================================
# 2. 화면 출력 및 AI 작성 엔진
# ==========================================
if st.button("🔥 실시간 돈 되는 공시 스캔하기", use_container_width=True):
    with st.spinner("금융감독원 DART 서버를 털어서 핵심 공시만 골라내는 중... 🕵️‍♂️"):
        hot_reports, error = get_hot_dart_reports()
        
        if error:
            st.error(error)
        elif not hot_reports:
            st.info("평화로운 주말이거나, 현재 시장에 뜬 굵직한 호재/악재 공시가 없습니다. 내일 다시 스캔해 보세요!")
        else:
            st.success(f"✅ 총 {len(hot_reports)}건의 돈 되는 공시를 포착했습니다!")
            
            reports_text = ""
            for i, r in enumerate(hot_reports):
                reports_text += f"- [{r['회사명']}] {r['공시제목']} (접수일: {r['접수일자']})\n"
                
            with st.expander("👀 포착된 원본 공시 리스트 보기"):
                st.write(reports_text)
                
            with st.spinner("AI 편집장이 공시 내용을 개미들 언어로 번역하여 보고서를 쓰는 중... ✍️"):
                # 💡 [프롬프트 핵심 수정] 메인 제목을 딱 1개만 출력하도록 강제합니다.
                prompt = f"""
                당신은 기업의 수석 투자 분석가이자 주식 블로그 '앤트리치'의 에디터입니다.
                아래는 최근 3일간 금융감독원 DART에서 올라온 가장 뜨거운 기업 공시 리스트입니다.
                
                {reports_text}
                
                이 공시들이 각각 시장에 미칠 영향(호재인지 악재인지)을 분석해서, 직장 상사에게 보고하는 형태의 분석 보고서를 작성해 주세요.

                [🚨 매우 중요한 작성 규칙]
                1. [어투 종결 강제]: 2~4번 항목의 모든 문장 끝은 무조건 "~함", "~됨", "~했음", "~예상됨", "~필요함" 형식의 개조식으로만 작성하세요.
                2. [기호 사용 완전 통제]: 글 전체에 걸쳐서 별표(*) 기호와 이모티콘(이모지)은 단 한 개도 절대 사용하지 마세요. 강조할 때는 대괄호([ ])나 꺾쇠(【 】)를 사용하세요.

                [출력 필수 구성 (순서대로 정확히 지킬 것)]
                ■ 1. 앤트리치 전용 메인 제목 (단 1개만)
                - (위 공시 중 가장 중요하거나 충격적인 종목 1~2개를 골라 아래 공식에 맞춰 딱 1줄의 제목만 작성할 것. 여러 개 제안 금지.)
                - 작성 공식: [긴급 팩트체크] 회사명 '공시 종류', 호재일까 악재일까?

                ■ 2. 팩트 요약 및 영향도 분석
                - (각 회사별로 공시의 의미가 무엇인지, 내일 주가에 호재인지 악재인지 팩트 기반으로 분석. 반드시 ~함, ~전망됨으로 끝낼 것)

                ■ 3. 투자 전략 (대응 방안)
                - (지금 매수해야 할지, 도망쳐야 할지 객관적 시선으로 전략 제안. 반드시 ~필요함, ~판단됨으로 끝낼 것)

                ■ 4. 🔥 앤트리치의 찐 속마음 (인간미 코멘트)
                - 앞의 딱딱한 분석을 끝내고, 3040 직장인 개미 투자자에게 완벽하게 빙의하세요. "형님들, 공시 뜬 거 보셨습니까? 내일 시초가에 무조건 던져야 합니다 ㅠㅠ", "세력 형님들이 장난치는 거니까 꽉 물고 계십쇼" 등 비표준어, 한탄, 유머, 인터넷 커뮤니티 말투를 듬뿍 섞어서 아주 찰지고 주관적인 코멘트를 2~3줄 툭 던지듯 작성해 주세요. AI 느낌을 0%로 만드세요.

                ■ 5. [🎨 이미지 AI용 만화 주문서]
                - 이 이슈를 다루는 주식 투자 개미 캐릭터의 상황을 4컷 만화로 기획하세요.
                - 반드시 아래 문장을 가장 먼저 출력하세요.
                "위 기획안을 바탕으로 이미지 4장을 생성해 줘. 합치지 말고 무조건 1컷당 1개의 이미지 파일로 분리해서 생성해 줘. 그리고 반드시 각 이미지 안의 말풍선에 해당 컷의 대사를 텍스트로 넣어줘."
                
                ■ 6. 블로그용 해시태그
                - (쉼표로 구분된 관련 키워드 10개)
                """
                
                try:
                    response = model.generate_content(prompt)
                    
                    # 💡 별표 및 이모티콘 물리적 살균
                    clean_text = response.text.replace('*', '')
                    clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text)
                    
                    st.divider()
                    st.subheader("📝 앤트리치 펀더멘털 공시 해석 보고서")
                    with st.container(border=True):
                        st.markdown(clean_text)
                        
                except ResourceExhausted:
                    st.error("🚨 AI 과부하 상태입니다. 잠시 후 다시 시도해 주세요!")
                except Exception as e:
                    st.error(f"🚨 알 수 없는 오류 발생: {e}")
