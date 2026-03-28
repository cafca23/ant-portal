import streamlit as st
import requests
import urllib.parse
import pandas as pd
from bs4 import BeautifulSoup
import google.generativeai as genai

# ==========================================
# 0. 초기 세팅
# ==========================================
st.set_page_config(page_title="여행/캠핑 딥다이브 봇", page_icon="🏕️", layout="wide")

st.title("🏕️ 전국 방방곡곡 여행/캠핑 딥다이브 봇")
st.write("관광공사의 정보를 투명하게 표로 모두 확인하고, 원하는 곳을 골라 심층 블로그를 작성합니다.")
st.divider()

try:
    public_api_key = st.secrets["GOV_API_KEY"].strip()
    gemini_api_key = st.secrets["GEMINI_API_KEY"].strip()
except KeyError:
    st.error("🚨 .streamlit/secrets.toml 파일에 API 키를 설정해주세요!")
    st.stop()

headers = {'User-Agent': 'Mozilla/5.0'}

# ==========================================
# 1. 공공데이터 통신 함수들 (원문 응답 추출기 탑재)
# ==========================================
@st.cache_data(ttl=86400, show_spinner=False)
def get_sigungu(api_key, a_code):
    base_url = "http://apis.data.go.kr/B551011/KorService1/areaCode1"
    full_url = f"{base_url}?serviceKey={api_key}&numOfRows=50&pageNo=1&MobileOS=ETC&MobileApp=App&_type=json&areaCode={a_code}"
    
    try:
        res = requests.get(full_url, timeout=10)
        # 💡 JSON 에러가 나기 전에 원본 텍스트(res.text)부터 무조건 확보!
        raw_text = res.text.strip()
        
        if raw_text.startswith('<'): # 서버가 JSON 대신 XML 에러를 뱉었을 경우
            return {"전체": ""}, f"[XML 에러 발생]\n{raw_text[:300]}"
            
        data = res.json()
        items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if isinstance(items, dict): items = [items]
        
        sigungu_dict = {"전체": ""}
        for item in items:
            if item.get('name'): sigungu_dict[item.get('name')] = item.get('code')
        return sigungu_dict, "정상 응답"
    except Exception as e: 
        return {"전체": ""}, f"[파이썬 에러]\n{str(e)}"

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_places(p_type, a_code, a_name, s_code, s_name):
    places = []
    debug_log = ""
    
    if "여행지" in p_type:
        base_url = "http://apis.data.go.kr/B551011/KorService1/areaBasedList1"
        full_url = f"{base_url}?serviceKey={public_api_key}&numOfRows=50&pageNo=1&MobileOS=ETC&MobileApp=App&_type=json&listYN=Y&arrange=A&contentTypeId=12&areaCode={a_code}"
        if s_code: 
            full_url += f"&sigunguCode={s_code}"
            
        try:
            res = requests.get(full_url, timeout=10)
            raw_text = res.text.strip()
            if raw_text.startswith('<'): return [], f"[XML 에러 발생]\n{raw_text[:300]}"
                
            debug_log = "정상 응답"
            items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if isinstance(items, dict): items = [items]
            for item in items:
                if item.get('title'): 
                    places.append({"장소명": item.get('title'), "주소": item.get('addr1', '주소 미상')})
        except Exception as e:
            debug_log = f"[파이썬 에러]\n{str(e)}"
            
    else:
        base_url = "http://apis.data.go.kr/B551011/GoCamping/searchList"
        korean_name_map = {"충북": "충청북도", "충남": "충청남도", "경북": "경상북도", "경남": "경상남도", "전북": "전라북도", "전남": "전라남도"}
        full_area = korean_name_map.get(a_name, a_name)
        keyword = full_area if s_name == "전체" else f"{full_area} {s_name}"
        
        encoded_keyword = urllib.parse.quote(keyword)
        full_url = f"{base_url}?serviceKey={public_api_key}&numOfRows=50&pageNo=1&MobileOS=ETC&MobileApp=App&_type=json&keyword={encoded_keyword}"
        
        try:
            res = requests.get(full_url, timeout=10)
            raw_text = res.text.strip()
            if raw_text.startswith('<'): return [], f"[XML 에러 발생]\n{raw_text[:300]}"
                
            debug_log = "정상 응답"
            items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if isinstance(items, dict): items = [items]
            for item in items:
                if item.get('facltNm'): 
                    places.append({"장소명": item.get('facltNm'), "주소": item.get('addr1', '주소 미상')})
        except Exception as e:
            debug_log = f"[파이썬 에러]\n{str(e)}"
            
    return places, debug_log

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
    base_url = "http://apis.data.go.kr/B551011/PhotoGalleryService1/gallerySearchList1"
    encoded_keyword = urllib.parse.quote(keyword)
    full_url = f"{base_url}?serviceKey={public_api_key}&numOfRows=2&pageNo=1&MobileOS=ETC&MobileApp=App&_type=json&keyword={encoded_keyword}"
    
    try:
        res = requests.get(full_url, timeout=10)
        items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if isinstance(items, dict): items = [items]
        return [p.get('galWebImageUrl', '') for p in items if p.get('galWebImageUrl')]
    except: return []

# ==========================================
# 2. 사이드바 설정 (지역 선택)
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
    selected_sigungu = st.selectbox("2. 시/군/구를 선택하세요:", list(sigungu_options.keys()))
    sigungu_code = sigungu_options[selected_sigungu]

# ==========================================
# 3. 메인 로직: 데이터 표 출력 및 포스팅
# ==========================================
display_region = f"{selected_area} {selected_sigungu if selected_sigungu != '전체' else ''}".strip()
st.subheader(f"📌 {display_region} {post_type.split(' ')[1]} 리스트")

with st.spinner("관광공사 데이터를 가져오는 중입니다..."):
    place_list, place_debug = fetch_places(post_type, area_code, selected_area, sigungu_code, selected_sigungu)

if not place_list:
    st.info("조건에 맞는 장소가 없거나 데이터를 불러오지 못했습니다. 아래 디버그 창을 확인해주세요.")
    with st.expander("🛠️ 시스템 디버그 (공공데이터포털 원본 응답)", expanded=True): # 자동으로 펼쳐지게 수정
        st.write("시군구 응답:", sigungu_debug)
        st.write("장소 응답:", place_debug)
else:
    st.write("📊 **한국관광공사 제공 데이터 (전체 리스트)**")
    df = pd.DataFrame(place_list)
    df.index = df.index + 1
    st.dataframe(df, use_container_width=True)
    st.divider()
    
    options = {f"{p['장소명']} ({p['주소']})": p for p in place_list}
    selected_label = st.selectbox("📝 위 표에서 분석할 장소 1곳을 선택하세요:", list(options.keys()))
    target_name = options[selected_label]['장소명']
    target_addr = options[selected_label]['주소']
    
    if st.button("✨ 이 장소로 심층 분석 블로그 자동 작성", type="primary", use_container_width=True):
        with st.spinner(f"[{target_name}] 웹 후기를 분석하고 포스팅을 작성 중입니다... ✍️"):
            
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
                
                st.subheader(f"📝 [{target_name}] 심층 포스팅 완료!")
                with st.container(border=True):
                    st.markdown(clean_result)
            except Exception as e:
                st.error(f"블로그 글 작성 중 오류가 발생했습니다: {e}")
