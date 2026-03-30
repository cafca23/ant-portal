import streamlit as st
import requests
from datetime import datetime, timedelta
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import re

# ==========================================
# 0. API 및 텔레그램 세팅 불러오기
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')
DART_API_KEY = st.secrets["DART_API_KEY"]

# 💡 텔레그램 암호키 불러오기
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

st.set_page_config(page_title="앤트리치 펀더멘털 스캐너", page_icon="🏢", layout="wide")

st.title("🏢 앤트리치 펀더멘털(공시) 스캐너")
st.write("돈이 되는 코스피/코스닥 핵심 공시만 필터링하여, 팩트 체크 보고서를 뽑아내고 텔레그램으로 즉시 쏩니다!")
st.divider()

# 💡 텔레그램으로 메시지를 쏘는 핵심 배관 함수
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

# ==========================================
# 1. DART 공시 데이터 수집 엔진
# ==========================================
def get_hot_dart_reports():
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
        
        if data.get("status") == "013":
            return [], None
        elif data.get("status") != "000":
            return None, f"DART 데이터 수집 실패 (상태코드: {data.get('status')})"
            
        reports = data.get("list", [])
        hot_keywords = ["유상증자", "무상증자", "단일판매", "공급계약", "자기주식", "영업잠정실적"]
        filtered_reports = []
        
        for r in reports:
            corp_cls = r.get("corp_cls", "")
            if corp_cls not in ["Y", "K"]:
                continue
                
            title = r.get("report_nm", "")
            if any(keyword in title for keyword in hot_keywords):
                raw_date = r.get("rcept_dt", "")
                formatted_date = f"{raw_date[:4]}년 {raw_date[4:6]}월 {raw_date[6:]}일" if len(raw_date) == 8 else raw_date

                filtered_reports.append({
                    "회사명": r.get("corp_nm", ""),
                    "종목코드": r.get("stock_code", ""),
                    "공시제목": title,
                    "제출인": r.get("flr_nm", ""),
                    "접수일자": formatted_date 
                })
                
        return filtered_reports[:5], None 
    except Exception as e:
        return None, f"서버 통신 에러: {e}"

# ==========================================
# 2. 화면 출력, AI 작성 및 텔레그램 전송 엔진
# ==========================================
if st.button("🔥 실시간 속보 스캔 & 텔레그램 발사!", use_container_width=True):
    with st.spinner("DART 서버에서 핵심 공시만 골라내는 중... 🕵️‍♂️"):
        hot_reports, error = get_hot_dart_reports()
        
        if error:
            st.error(error)
        elif not hot_reports:
            st.info("현재 시장에 뜬 굵직한 호재/악재 상장사 공시가 없습니다.")
        else:
            st.success(f"✅ 총 {len(hot_reports)}건의 돈 되는 공시 포착 완료!")
            
            reports_text = ""
            for i, r in enumerate(hot_reports):
                reports_text += f"- [타겟종목: {r['회사명']}] (종목코드: {r['종목코드']}) / 공시제목: {r['공시제목']} / 공시일자: {r['접수일자']}\n"
                
            with st.spinner("AI 편집장이 보고서를 쓰는 중... ✍️"):
                prompt = f"""
                당신은 기업의 수석 투자 분석가이자 주식 블로그 '앤트리치'의 에디터입니다.
                아래는 DART에서 방금 수집된 공시 리스트입니다.
                
                [공시 데이터]
                {reports_text}
                
                [🚨 초강력 작성 규칙 - 절대 엄수 (거짓말/소설 작성 금지)]
                1. [팩트 엄수]: 당신은 실제 공시 문서의 본문을 읽지 못했습니다. 따라서 제공된 [공시 데이터]의 '공시제목' 외에, 구체적인 금액, 사유, 일정 등을 절대 상상해서 지어내지 마세요. (환각 현상 금지)
                2. [타겟 1개 선정]: 리스트 중 주가에 가장 큰 영향을 미칠 딱 1개의 타겟종목만 메인으로 선정하세요.
                3. [분석의 한계 명시]: 상세 내용을 지어내는 대신, 해당 '공시 제목(예: 유상증자, 단일판매 등)'이 일반적으로 주식 시장에서 호재인지 악재인지, 투자자들이 어떤 점을 주의해야 하는지 '일반적인 관점'에서 해설하세요.
                4. [실명 사용 강제]: [타겟종목]의 진짜 이름 뒤에 종목코드를 괄호로 붙이세요. (예: 삼성전자(005930))
                5. [가독성 강제]: ■ 기호가 붙은 제목 뒤에는 반드시 엔터(Enter)를 쳐서 줄바꿈 하세요.
                6. [어투/기호 통제]: 문장은 무조건 "~함", "~됨", "~예상됨", "~필요함"으로 끝내고, 별표(*)와 이모티콘은 절대 쓰지 마세요.

                [출력 필수 구성 (순서대로 정확히 지킬 것)]
                ■ 1. 앤트리치 전용 메인 제목
                [긴급 팩트체크] 진짜이름(종목코드) '공시제목', 호재일까 악재일까?

                ■ 2. [공시일자: 데이터의 접수일자 기입] 공시의 의미와 시장의 시선
                (반드시 줄바꿈 후 작성) 선택한 공시가 일반적으로 주가에 어떤 영향을 미치는지 원론적이고 객관적인 해설 작성. (절대 없는 사실을 지어내지 말 것)

                ■ 3. 투자 전략 및 체크포인트
                (반드시 줄바꿈 후 작성) 투자자가 HTS나 DART 본문을 통해 추가로 확인해야 할 체크포인트 제시.

                ■ 4. 🔥 앤트리치의 말말말
                (반드시 줄바꿈 후 작성) 3040 개미 투자자에게 빙의하여 찰진 코멘트 작성.
                
                ■ 5. 정보 출처 및 블로그 안내 링크
                (반드시 줄바꿈 후 작성) 아래 두 문장을 그대로 똑같이 출력하세요:
                "🔎 본 정보의 출처는 금융감독원 전자공시시스템(DART)입니다. (https://dart.fss.or.kr/)"
                "👉 더 자세한 투자 포인트는 앤트리치 블로그에서 확인하세요! (https://blog.naver.com/antrich10)"
                """
                
                try:
                    response = model.generate_content(prompt)
                    clean_text = response.text.replace('*', '')
                    clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text)
                    
                    st.divider()
                    st.subheader("📝 앤트리치 펀더멘털 공시 해석 보고서")
                    with st.container(border=True):
                        st.markdown(clean_text)
                        
                    # 💡 대망의 텔레그램 전송 파트!
                    with st.spinner("📲 텔레그램 채널로 속보를 전송하는 중..."):
                        if send_telegram_message(clean_text):
                            st.success("🎉 텔레그램 채널에 성공적으로 속보가 발송되었습니다! 스마트폰 알림을 확인해 보세요!")
                        else:
                            st.error("🚨 텔레그램 전송 실패. secrets.toml의 토큰과 채널 아이디를 다시 확인해 주세요.")
                            
                except Exception as e:
                    st.error(f"🚨 오류 발생: {e}")
