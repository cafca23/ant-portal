import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup
import google.generativeai as genai

# ==========================================
# 0. 초기 세팅
# ==========================================
st.set_page_config(page_title="여행/캠핑 딥다이브 봇", page_icon="🏕️", layout="wide")

st.title("🏕️ 전국 방방곡곡 여행/캠핑 딥다이브 봇")
st.write("원하는 시/군/구까지 핀셋으로 집어내어 '진짜 팩트 기반'의 심층 블로그 포스팅을 작성합니다.")
st.divider()

# API 키 불러오기
try:
    public_api_key = st.secrets["GOV_API_KEY"]
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("🚨 .streamlit/secrets.toml 파일에 TOUR_API_KEY 와 GEMINI_API_KEY 를 설정해주세요!")
    st.stop()

headers = {'User-Agent': 'Mozilla/5.0'}

# ==========================================
# 1. 공공데이터 통신 함수들 (시군구 조회 포함)
# ==========================================
@st.cache_data(ttl=86400, show_spinner=False)
def get_sigungu(api_key, a_code):
    # 선택한 지역의 '시/군/구' 리스트를 가져옵니다.
    url = "http://apis.data.go.kr/B551011/KorService1/areaCode1"
    params = {
        "serviceKey": api_key, "numOfRows": "50", "pageNo": "1",
        "MobileOS": "ETC", "MobileApp": "App", "_type": "json", "areaCode": a_code
    }
    query = urllib.parse.urlencode(params, safe="%")
    try:
        res = requests.get(f"{url}?{query}", timeout=5)
        items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
        
        # API 결과가 1개일 때 딕셔너리로 오는 오류 방지
        if isinstance(items, dict):
            items = [items]
            
        sigungu_dict = {"전체": ""}
        for item in items:
            sigungu_dict[item.get('name')] = item.get('code')
        return sigungu_dict
    except:
        return {"전체": ""}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_places(p_type, a_code, a_name, s_code, s_name):
    places = []
    if "여행지" in p_type:
        url = "http://apis.data.go.kr/B551011/KorService1/areaBasedList1"
        params = {
            "serviceKey": public_api_key, "numOfRows": "30", "pageNo": "1",
            "MobileOS": "ETC", "MobileApp": "App", "_type": "json",
            "listYN": "Y", "arrange": "Q", "contentTypeId": "12", "areaCode": a_code
        }
        if s_code: # 시/군/구를 선택했다면 추가
            params["sigunguCode"] = s_code
            
        query = urllib.parse.urlencode(params, safe="%")
        try:
            res = requests.get(f"{url}?{query}", timeout=5)
            items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if isinstance(items, dict): items = [items]
            for item in items:
                name = item.get('title')
                if name: places.append(item)
        except: pass
    else:
        # 캠핑장은 이름(키워드) 기반 검색이 훨씬 정확합니다.
        url = "http://apis.data.go.kr/B551011/GoCamping/searchList"
        keyword = a_name if s_name == "전체" else f"{a_name} {s_name}"
        params = {
            "serviceKey": public_api_key, "numOfRows": "30", "pageNo": "1",
            "MobileOS": "ETC", "MobileApp": "App", "_type": "json", "keyword": keyword
        }
        query = urllib.parse.urlencode(params, safe="%")
        try:
            res = requests.get(f"{url}?{query}", timeout=5)
            items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if isinstance(items, dict): items = [items]
            for item in items:
                name = item.get('facltNm')
                if name: places.append(item)
        except: pass
    return places

def scrape_web_info(keyword):
    scraped_data = []
    try:
        clean_keyword = urllib.parse.quote(f"{keyword} 후기 OR 리뷰")
        url = f"https://news.google.com/rss/search?q={clean_keyword}&hl=ko&gl=KR&ceid=KR:ko"
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        for item in soup.find_all("item")[:7]:
            scraped_data.append(item.title.text)
    except: pass
    return "\n".join(scraped_data) if scraped_data else "관련 검색 결과가 부족합니다."

def get_exact_photo(keyword):
    url = "http://apis.data.go.kr/B551011/PhotoGalleryService1/gallerySearchList1"
    params = {
        "serviceKey": public_api_key, "numOfRows": "2", "pageNo": "1",
        "MobileOS": "ETC", "MobileApp": "App", "_type": "json", "keyword": keyword
    }
    query = urllib.parse.urlencode(params, safe="%")
    try:
        res = requests.get(f"{url}?{query}", timeout=5)
        items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if isinstance(items, dict): items = [items]
        return [p.get('galWebImageUrl', '') for p in items if p.get('galWebImageUrl')]
    except: return []

# ==========================================
# 2. 사이드바 설정 (2단계 지역 선택)
# ==========================================
with st.sidebar:
    st.header("⚙️ 검색 설정")
    post_type = st.radio("어떤 주제로 포스팅할까요?", ["📸 여행지/관광지", "⛺ 캠핑장"])
    
    st.divider()
    # 대한민국 전국 17개 시/도 모두 추가!
    area_options = {
        "서울": "1", "인천": "2", "대전": "3", "대구": "4", "광주": "5", "부산": "6", "울산": "7", "세종": "8", 
        "경기": "31", "강원": "32", "충북": "33", "충남": "34", "경북": "35", "경남": "36", "전북": "37", "전남": "38", "제주": "39"
    }
    selected_area = st.selectbox("1. 광역시/도를 선택하세요:", list(area_options.keys()))
    area_code = area_options[selected_area]
    
    # 선택한 지역의 시군구를 API로 즉시 불러와서 두 번째 드롭다운 생성
    sigungu_options = get_sigungu(public_api_key, area_code)
    selected_sigungu = st.selectbox("2. 시/군/구를 선택하세요:", list(sigungu_options.keys()))
    sigungu_code = sigungu_options[selected_sigungu]

# ==========================================
# 3. 메인 로직: 타겟 리스트업 및 포스팅
# ==========================================
display_region = f"{selected_area} {selected_sigungu if selected_sigungu != '전체' else ''}".strip()
st.subheader(f"📌 {display_region} {post_type.split(' ')[1]} 리스트")

with st.spinner("한국관광공사 데이터베이스를 뒤지고 있습니다..."):
    place_list = fetch_places(post_type, area_code, selected_area, sigungu_code, selected_sigungu)

if not place_list:
    st.info("해당 조건에 맞는 장소가 없거나, 공공데이터 서버 응답이 지연되고 있습니다. 다른 지역을 선택해 보세요.")
else:
    options = {}
    for p in place_list:
        name = p.get('title') or p.get('facltNm')
        addr = p.get('addr1', '주소 미상')
        options[f"{name} ({addr})"] = p
        
    selected_label = st.selectbox("📝 포스팅할 장소를 단 1곳만 선택하세요:", list(options.keys()))
    target_place = options[selected_label]
    target_name = target_place.get('title') or target_place.get('facltNm')
    target_addr = target_place.get('addr1', '주소 미상')
    
    st.write(f"**타겟 확정:** `{target_name}`")
    
    if st.button("✨ 이 장소로 심층 분석 블로그 자동 작성", type="primary", use_container_width=True):
        with st.spinner(f"[{target_name}] 네이버/구글 후기를 스크래핑하고 포스팅을 작성 중입니다... ✍️"):
            
            web_info = scrape_web_info(target_name)
            photos = get_exact_photo(target_name)
            
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = f"""
            당신은 대한민국 구석구석을 누비며 디테일한 정보를 전달하는 '국내 여행/캠핑 전문 파워 블로거'입니다.
            이번 포스팅의 단일 타겟 장소는 [{target_name}](위치: {target_addr}) 입니다.
            
            [수집된 실제 웹 후기/정보 텍스트]
            {web_info}
            
            위의 실제 후기 정보와 당신의 지식을 바탕으로, 네이버 블로그에 바로 올릴 수 있는 심층 분석 포스팅을 작성해 주세요.

            [🚨 중요 작성 가이드라인]
            1. 분산 금지: 다른 장소를 추천하지 마세요. 오직 '{target_name}' 딱 한 곳의 매력, 시설, 장점, 주의할 점에 대해서만 깊이 있게 분석하세요.
            2. 실전 정보: 수집된 웹 후기 텍스트를 참고하여, 실제 방문자만 알 수 있는 디테일(주차 팁, 명당 자리, 주변 핫플, 준비물 등)을 반드시 포함하세요.
            3. 사진 삽입: 글 중간에 아래의 마크다운 코드를 자연스럽게 배치하세요.
               사진1: ![풍경1]({photos[0] if len(photos) > 0 else ''})
               사진2: ![풍경2]({photos[1] if len(photos) > 1 else ''})
            4. 마무리 및 3줄 요약: 글의 마지막에 [바쁜 분들을 위한 3줄 요약] 이라는 소제목과 함께 사람이 직접 쓴 것처럼 자연스러운 3줄 요약을 반드시 추가하세요.
            5. 해시태그: SEO 최적화를 위해 관련 키워드 10개를 넣어주세요.
            6. 🚫 [절대 금지 사항]: 글 전체에 어떠한 이모지(이모티콘)도 절대 사용하지 마세요. 강조나 리스트를 위해 별표 기호(*)도 절대 사용하지 마세요. 리스트 기호가 필요하다면 하이픈(-)이나 숫자를 사용하세요.
            """
            
            try:
                response = model.generate_content(prompt)
                clean_result = response.text.replace('*', '')
                
                st.divider()
                st.subheader(f"📝 [{target_name}] 심층 포스팅 완료!")
                with st.container(border=True):
                    st.markdown(clean_result)
            except Exception as e:
                st.error(f"블로그 글 작성 중 오류가 발생했습니다: {e}")
