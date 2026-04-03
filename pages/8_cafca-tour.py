import streamlit as st
import requests
import urllib.parse
import pandas as pd
from bs4 import BeautifulSoup
import google.generativeai as genai
import re  # 💡 이모티콘 및 기호 살균을 위한 정규식 모듈 추가
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# ==========================================
# 0. 초기 세팅 (Tier 1 무제한 엔진 장착)
# ==========================================
st.set_page_config(page_title="주말 나들이 & 캠핑 봇", page_icon="🏕️", layout="wide")

st.title("🏕️ 주말 어디 가지? (나들이+캠핑 딥다이브 봇 V4 Pro)")
st.write("원하는 지역의 관광지/캠핑장을 고르면, AI가 실제 후기를 분석해 시원시원한 가독성의 파워 블로그를 작성해 줍니다.")
st.divider()

try:
    public_api_key = urllib.parse.unquote(st.secrets["GOV_API_KEY"].strip()) 
    gemini_api_key = st.secrets["GEMINI_API_KEY"].strip()
except KeyError:
    st.error("🚨 .streamlit/secrets.toml 파일에 API 키를 설정해주세요!")
    st.stop()

# 💡 고도화 1: 무제한 API에 맞춘 AI 두뇌 세팅 (출력 한도 8000 상향)
genai.configure(api_key=gemini_api_key)
generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 8000,
}
model = genai.GenerativeModel('gemini-2.5-flash', generation_config=generation_config)

headers = {'User-Agent': 'Mozilla/5.0'}

# ==========================================
# 1. 통신 함수들 (엑스레이 탑재)
# ==========================================
@st.cache_data(ttl=86400, show_spinner=False)
def get_sigungu(api_key, a_code):
    url = "https://apis.data.go.kr/B551011/KorService1/areaCode1"
    params = {"serviceKey": api_key, "numOfRows": "50", "pageNo": "1", "MobileOS": "ETC", "MobileApp": "App", "_type": "json", "areaCode": a_code}
    try:
        res = requests.get(url, params=params, timeout=10)
        raw_text = res.text.strip()
        if not raw_text.startswith('{'): 
            return {"전체": ""}, raw_text 
        
        items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if isinstance(items, dict): items = [items]
        sigungu_dict = {"전체": ""}
        for item in items:
            if item.get('name'): sigungu_dict[item.get('name')] = item.get('code')
        return sigungu_dict, "정상"
    except Exception as e: 
        return {"전체": ""}, str(e)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_places(p_type, a_code, a_name, s_code, s_name):
    places = []
    
    if "여행지" in p_type:
        url = "https://apis.data.go.kr/B551011/KorService1/areaBasedList1"
        params = {"serviceKey": public_api_key, "numOfRows": "50", "pageNo": "1", "MobileOS": "ETC", "MobileApp": "App", "_type": "json", "listYN": "Y", "arrange": "A", "contentTypeId": "12", "areaCode": a_code}
        if s_code: params["sigunguCode"] = s_code
        try:
            res = requests.get(url, params=params, timeout=10)
            raw_text = res.text.strip()
            
            if not raw_text.startswith('{'): 
                st.error(f"🚨 [정부 서버 에러 원문]\n\n{raw_text[:500]}")
                return []
                
            items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if isinstance(items, dict): items = [items]
            for item in items:
                if item.get('title'): places.append({"장소명": item.get('title'), "주소": item.get('addr1', '주소 미상')})
        except Exception as e:
            st.error(f"파이썬 에러: {e}")
            
    else:
        url = "https://apis.data.go.kr/B551011/GoCamping/searchList"
        korean_name_map = {"충북": "충청북도", "충남": "충청남도", "경북": "경상북도", "경남": "경상남도", "전북": "전라북도", "전남": "전라남도"}
        full_area = korean_name_map.get(a_name, a_name)
        keyword = full_area if s_name == "전체" else f"{full_area} {s_name}"
        params = {"serviceKey": public_api_key, "numOfRows": "50", "pageNo": "1", "MobileOS": "ETC", "MobileApp": "App", "_type": "json", "keyword": keyword}
        try:
            res = requests.get(url, params=params, timeout=10)
            raw_text = res.text.strip()
            if not raw_text.startswith('{'): 
                st.error(f"🚨 [정부 서버 에러 원문]\n\n{raw_text[:500]}")
                return []
                
            items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if isinstance(items, dict): items = [items]
            for item in items:
                if item.get('facltNm'): places.append({"장소명": item.get('facltNm'), "주소": item.get('addr1', '주소 미상')})
        except Exception as e:
            st.error(f"파이썬 에러: {e}")
            
    return places

def scrape_web_info(keyword):
    scraped_data = []
    try:
        clean_keyword = urllib.parse.quote(f"{keyword} 후기 OR 리뷰")
        url = f"https://news.google.com/rss/search?q={clean_keyword}&hl=ko&gl=KR&ceid=KR:ko"
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        for item in soup.find_all("item")[:7]: scraped_data.append(item.title.text)
    except: pass
    return "\n".join(scraped_data) if scraped_data else "관련 검색 결과가 부족합니다."

def get_exact_photo(keyword):
    url = "https://apis.data.go.kr/B551011/PhotoGalleryService1/gallerySearchList1"
    params = {"serviceKey": public_api_key, "numOfRows": "2", "pageNo": "1", "MobileOS": "ETC", "MobileApp": "App", "_type": "json", "keyword": keyword}
    try:
        res = requests.get(url, params=params, timeout=10)
        if not res.text.strip().startswith('{'): return []
        items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if isinstance(items, dict): items = [items]
        return [p.get('galWebImageUrl', '') for p in items if p.get('galWebImageUrl')]
    except: return []

# ==========================================
# 2. 사이드바 설정
# ==========================================
with st.sidebar:
    st.header("⚙️ 검색 설정")
    post_type = st.radio("어떤 주제로 포스팅할까요?", ["📸 여행지/관광지", "⛺ 캠핑장"]) 
    st.divider()
    
    area_options = {
        "서울": "1", "인천": "2", "대전": "3", "대구": "4", "광주": "5", "부산": "6", "울산": "7", "세종": "8", 
        "경기": "31", "강원": "32", "충북": "33", "충남": "34", "경북": "35", "경남": "36", "전북": "37", "전남": "38", "제주": "39"
    }
    selected_area = st.selectbox("1. 광역시/도를 선택하세요:", list(area_options.keys()))
    area_code = area_options[selected_area]
    
    sigungu_options, sigungu_debug = get_sigungu(public_api_key, area_code)
    
    if sigungu_debug != "정상":
        st.error(f"시군구 동기화 대기중: {sigungu_debug[:100]}")
        
    selected_sigungu = st.selectbox("2. 시/군/구를 선택하세요:", list(sigungu_options.keys()))
    sigungu_code = sigungu_options[selected_sigungu]

# ==========================================
# 3. 메인 로직
# ==========================================
display_region = f"{selected_area} {selected_sigungu if selected_sigungu != '전체' else ''}".strip()
st.subheader(f"📌 {display_region} {post_type.split(' ')[1]} 리스트")

with st.spinner("데이터를 가져오는 중입니다..."):
    place_list = fetch_places(post_type, area_code, selected_area, sigungu_code, selected_sigungu)

if not place_list:
    st.info(f"데이터가 없습니다. 위 붉은색 에러 창에 'SERVICE_KEY_IS_NOT_REGISTERED_ERROR'가 뜬다면 동기화 진행 중입니다.")
else:
    df = pd.DataFrame(place_list)
    df.index = df.index + 1
    st.dataframe(df, use_container_width=True)
    st.divider()
    
    options = {f"{p['장소명']} ({p['주소']})": p for p in place_list}
    selected_label = st.selectbox("📝 위 표에서 분석할 장소 1곳을 선택하세요:", list(options.keys()))
    target_name = options[selected_label]['장소명']
    target_addr = options[selected_label]['주소']
    
    if st.button("✨ 이 장소로 심층 분석 블로그 자동 작성", type="primary", use_container_width=True):
        with st.spinner(f"[{target_name}] 웹 후기를 긁어모아 블로그 글을 작성 중입니다... ✍️ (무제한 엔진 가동)"):
            web_info = scrape_web_info(target_name)
            photos = get_exact_photo(target_name)
            
            prompt = f"""당신은 국내 여행/캠핑 전문 파워 블로거입니다. 타겟 장소는 [{target_name}](위치: {target_addr}) 입니다.
            
            [웹 후기 텍스트]
            {web_info}
            
            위 후기를 바탕으로, '{target_name}' 한 곳만 깊이 있게 분석하는 네이버 블로그 포스팅을 작성하세요.
            
            [🚨 매우 중요한 작성 규칙]
            1. 글의 흐름 중간에 어울리는 위치를 찾아 반드시 아래의 사진 태그 두 개를 정확히 삽입하세요:
               사진1: ![풍경1]({photos[0] if len(photos) > 0 else ''})
               사진2: ![풍경2]({photos[1] if len(photos) > 1 else ''})
            2. 마지막엔 [바쁜 분들을 위한 3줄 요약]을 추가하세요.
            3. 기호 통제: 글 전체에 걸쳐 이모지(이모티콘)와 별표(*)는 단 한 개도 절대 사용하지 마세요.
            4. [줄바꿈 강제]: 가독성을 위해 본문을 작성할 때 문장이 마침표(.)로 끝나면, 무조건 줄바꿈(엔터)을 하여 다음 내용이 새로운 줄에서 시작되도록 하세요.
            """
            
            try:
                response = model.generate_content(prompt)
                st.subheader(f"📝 [{target_name}] 무제한 엔진 심층 포스팅 완료!")
                
                with st.container(border=True):
                    # 💡 [핵심] 파이썬 물리적 살균 및 100% 강제 줄바꿈
                    clean_text = response.text.replace("*", "")
                    clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text)
                    clean_text = clean_text.replace(". ", ".\n\n")
                    
                    st.markdown(clean_text)
            except Exception as e: 
                st.error(f"작성 오류: {e}")
