import streamlit as st
import requests
import urllib.parse
from datetime import datetime
import google.generativeai as genai

# ==========================================
# 0. 초기 세팅
# ==========================================
st.set_page_config(page_title="주말 나들이 & 캠핑 자동화 봇", page_icon="🏕️", layout="wide")

st.title("🏕️ 이번 주말 어디 가지? (나들이+캠핑 융합 봇)")
st.write("관광공사 축제, 전국 캠핑장, 고화질 갤러리 API를 융합해 '아빠표 실전 블로그'를 자동 생성합니다.")
st.divider()

with st.sidebar:
    st.header("🔑 API 설정")
    st.info("API 키가 코드 안에 안전하게 저장되어 있습니다.")
    
    # st.text_input 을 지우고, 대표님의 진짜 키를 직접 따옴표 안에 넣어줍니다.
    public_api_key = st.secrets["GOV_API_KEY"]
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
    
    st.divider()
    st.header("⚙️ 검색 설정")
    area_options = {
        "서울": "1", "인천": "2", "대전": "3", "대구": "4", 
        "광주": "5", "부산": "6", "울산": "7", "세종": "8", "경기": "31", "강원": "32"
    }
    selected_area = st.selectbox("어느 지역으로 떠날까요?", list(area_options.keys()))
    area_code = area_options[selected_area]

# ==========================================
# 1. API 데이터 수집 함수들 (축제, 캠핑, 사진)
# ==========================================
def get_festivals(api_key, area_code):
    url = "http://apis.data.go.kr/B551011/KorService1/searchFestival1"
    today = datetime.today().strftime("%Y%m") + "01"
    params = {
        "serviceKey": api_key, "numOfRows": "3", "pageNo": "1",
        "MobileOS": "ETC", "MobileApp": "AntrichBlog", "_type": "json",
        "listYN": "Y", "arrange": "A", "eventStartDate": today, "areaCode": area_code
    }
    query = urllib.parse.urlencode(params, safe="%")
    try:
        res = requests.get(f"{url}?{query}", timeout=5)
        return res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
    except: return []

def get_campings(api_key, keyword):
    url = "http://apis.data.go.kr/B551011/GoCamping/searchList"
    params = {
        "serviceKey": api_key, "numOfRows": "2", "pageNo": "1",
        "MobileOS": "ETC", "MobileApp": "AntrichBlog", "_type": "json", "keyword": keyword
    }
    query = urllib.parse.urlencode(params, safe="%")
    try:
        res = requests.get(f"{url}?{query}", timeout=5)
        return res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
    except: return []

def get_photos(api_key, keyword):
    url = "http://apis.data.go.kr/B551011/PhotoGalleryService1/gallerySearchList1"
    params = {
        "serviceKey": api_key, "numOfRows": "3", "pageNo": "1",
        "MobileOS": "ETC", "MobileApp": "AntrichBlog", "_type": "json", "keyword": keyword
    }
    query = urllib.parse.urlencode(params, safe="%")
    try:
        res = requests.get(f"{url}?{query}", timeout=5)
        return res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
    except: return []

# ==========================================
# 2. 메인 실행 로직
# ==========================================
if st.button("🚀 이번 주말 축제+캠핑장 정보 긁어오기", type="primary", use_container_width=True):
    if not public_api_key or not gemini_api_key:
        st.warning("👈 왼쪽 사이드바에 공공데이터 키와 Gemini 키를 모두 입력해 주세요!")
    else:
        with st.spinner(f"📡 {selected_area} 지역의 축제, 캠핑장, 고화질 사진을 싹 다 긁어오고 있습니다..."):
            
            # 1. 데이터 수집
            festivals = get_festivals(public_api_key, area_code)
            campings = get_campings(public_api_key, selected_area)
            photos = get_photos(public_api_key, selected_area)
            
            if not festivals and not campings:
                st.error("데이터를 불러오지 못했습니다. 공공데이터포털 API 키가 정확한지, 혹은 승인이 완료되었는지 확인해 주세요.")
            else:
                st.success("🎉 성공적으로 3종 세트 데이터를 모두 확보했습니다!")
                
                # 2. 수집된 데이터를 AI에게 먹이기 좋게 텍스트로 정리
                raw_text = f"--- [{selected_area} 지역 축제 정보] ---\n"
                for f in festivals:
                    raw_text += f"- 축제명: {f.get('title', '')} (기간: {f.get('eventstartdate', '')}~{f.get('eventenddate', '')})\n"
                    raw_text += f"  주소: {f.get('addr1', '')}\n"
                
                raw_text += f"\n--- [{selected_area} 지역 추천 가족 캠핑장] ---\n"
                for c in campings:
                    raw_text += f"- 캠핑장명: {c.get('facltNm', '')} (주소: {c.get('addr1', '')})\n"
                    raw_text += f"  특징/부대시설: {c.get('sbrsCl', '')}\n"
                    raw_text += f"  반려동물: {c.get('animalCmgCl', '')}\n"

                photo_urls = [p.get('galWebImageUrl', '') for p in photos if p.get('galWebImageUrl')]
                
                with st.expander("🔍 긁어온 원본 데이터 확인 (Raw Data)"):
                    st.text(raw_text)
                    for url in photo_urls:
                        st.write(url)

# ==========================================
# 3. Gemini 연동: 국내 여행 전문 블로그 자동 완성
# ==========================================
                with st.spinner("✍️ 누구나 훌쩍 떠나고 싶게 만드는 감성 가득한 여행 블로그 글을 작성 중입니다..."):
                    genai.configure(api_key=gemini_api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    prompt = f"""
                    당신은 대한민국 구석구석 숨겨진 보석 같은 여행지와 캠핑장을 소개하는 '국내 여행 전문 파워 블로거'입니다.
                    다음은 한국관광공사 API를 통해 방금 긁어온 이번 주 '{selected_area}' 지역의 최신 축제와 캠핑장 데이터입니다.
                    
                    {raw_text}
                    
                    이 데이터를 바탕으로 네이버 블로그에 바로 복사해서 올릴 수 있는 기가 막힌 포스팅을 작성해 주세요.

                    [🚨 중요 작성 가이드라인]
                    1. 도입부: 바쁜 일상에 지쳐 다가오는 주말 힐링 여행을 꿈꾸는 직장인, 연인, 가족 등 누구나 100% 공감할 수 있는 감성적이고 친근한 말투로 시작하세요.
                    2. 코스 제안: '낮에는 지역 축제의 활기를 만끽하고, 밤에는 낭만적인 캠핑장에서 자연과 함께 쉬어가는 완벽한 주말 코스'라는 콘셉트로 축제와 캠핑장 정보를 매끄럽게 엮어주세요.
                    3. 실전 꿀팁 묘사: 주차 난이도, 화장실 청결 상태, 주변 편의점이나 핫플 유무 등 남녀노소 누가 가더라도 방문 전 꼭 알아야 할 '프로 여행러'의 실전 꿀팁을 가상으로 덧붙여 신뢰도를 높여주세요.
                    4. 사진 삽입: 글 중간중간에 아래의 이미지 마크다운 코드를 적절히 배치해서 글과 사진이 어우러지게 해주세요.
                       사진1: ![풍경1]({photo_urls[0] if len(photo_urls) > 0 else ''})
                       사진2: ![풍경2]({photo_urls[1] if len(photo_urls) > 1 else ''})
                    5. 마무리 및 3줄 요약: 이번 주말 당장 떠나고 싶게 만드는 따뜻한 마무리 멘트를 작성한 뒤, 그 바로 밑에 [바쁜 분들을 위한 3줄 요약] 이라는 소제목과 함께 사람이 직접 쓴 것처럼 자연스럽고 위트 있는 3줄 요약을 반드시 추가하세요. 
                       (예시: 1. 낮에는 OO축제에서 인생샷 건지기 / 2. 저녁엔 OO캠핑장에서 고기 굽고 불멍타임 / 3. 주차는 제2공영주차장이 꿀입니다요!)
                    6. 해시태그: SEO 최적화를 위해 글 맨 아래에 해시태그 10개를 넣어주세요.
                    7. 🚫 [절대 금지 사항]: 글 전체에 어떠한 이모지(이모티콘)도 절대 사용하지 마세요. 또한 강조나 리스트를 위해 별표 기호도 절대 사용하지 마세요. 리스트 기호가 필요하다면 하이픈(-)이나 숫자를 사용하세요.
                    """
                    
                    try:
                        response = model.generate_content(prompt)
                        
                        # 💡 파이썬 단에서 혹시 모를 * 기호를 강제로 싹 지워버립니다.
                        clean_result_text = response.text.replace('*', '')
                        
                        st.divider()
                        st.subheader("📝 여행 전문 블로거 포스팅 완성!")
                        with st.container(border=True):
                            st.markdown(clean_result_text)
                    except Exception as e:
                        st.error(f"블로그 글 작성 중 오류가 발생했습니다: {e}")
