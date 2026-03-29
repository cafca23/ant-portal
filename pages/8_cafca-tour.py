import streamlit as st
import requests
import pandas as pd

# ==========================================
# 0. 초기 세팅
# ==========================================
st.set_page_config(page_title="공공데이터 원본 추출기", layout="wide")

st.title("🚨 공공데이터 원본 100개 추출기 (필터 없음)")
st.write("지역 선택이나 검색어 없이, 정부 서버에 있는 전국 데이터를 그대로 100개만 가져옵니다.")
st.divider()

# API 키 세팅
try:
    public_api_key = st.secrets["GOV_API_KEY"].strip()
except KeyError:
    st.error("🚨 .streamlit/secrets.toml 파일에 TOUR_API_KEY 를 설정해주세요!")
    st.stop()

# ==========================================
# 1. 3가지 원본 호출 버튼
# ==========================================
col1, col2, col3 = st.columns(3)

# 1) 관광지 호출 (areaCode=1 서울 강제 주입)
if col1.button("🗺️ 1. 관광지 100개 가져오기 (서울 테스트)", use_container_width=True):
    with st.spinner("관광지 데이터 호출 중..."):
        # 💡 핵심 해결책: 끝에 &areaCode=1 (서울)을 강제로 넣어서 정부 서버가 뻗지 않게 달래줍니다.
        url = f"https://apis.data.go.kr/B551011/KorService1/areaBasedList1?serviceKey={public_api_key}&numOfRows=100&pageNo=1&MobileOS=ETC&MobileApp=App&_type=json&listYN=Y&arrange=A&contentTypeId=12&areaCode=1"
        
        try:
            res = requests.get(url, timeout=15)
            raw_text = res.text.strip()
            
            st.subheader("응답 결과")
            if not raw_text.startswith('{'):
                st.error(f"서버 에러 발생 [HTTP {res.status_code}]\n\n{raw_text[:500]}")
            else:
                st.success("✅ 1번 관광지 통신 성공!")
                items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
                if isinstance(items, dict): items = [items]
                
                df = pd.DataFrame(items)
                st.dataframe(df, use_container_width=True)
                
                with st.expander("원본 JSON 데이터 보기"):
                    st.json(items)
        except Exception as e:
            st.error(f"파이썬 통신 에러: {e}")

# 2) 전국 캠핑장 호출
if col2.button("⛺ 2. 전국 캠핑장 100개 가져오기", use_container_width=True):
    with st.spinner("전국 캠핑장 데이터 호출 중..."):
        url = f"https://apis.data.go.kr/B551011/GoCamping/basedList?serviceKey={public_api_key}&numOfRows=100&pageNo=1&MobileOS=ETC&MobileApp=App&_type=json"
        
        try:
            res = requests.get(url, timeout=15)
            raw_text = res.text.strip()
            
            st.subheader("응답 결과")
            if not raw_text.startswith('{'):
                st.error(f"서버 에러 발생 [HTTP {res.status_code}]\n\n{raw_text[:500]}")
            else:
                st.success("✅ 2번 캠핑장 통신 성공!")
                items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
                if isinstance(items, dict): items = [items]
                
                df = pd.DataFrame(items)
                st.dataframe(df, use_container_width=True)
                
                with st.expander("원본 JSON 데이터 보기"):
                    st.json(items)
        except Exception as e:
            st.error(f"파이썬 통신 에러: {e}")

# 3) 전국 관광사진 호출
if col3.button("📸 3. 전국 관광사진 100개 가져오기", use_container_width=True):
    with st.spinner("전국 관광사진 데이터 호출 중..."):
        url = f"https://apis.data.go.kr/B551011/PhotoGalleryService1/galleryList1?serviceKey={public_api_key}&numOfRows=100&pageNo=1&MobileOS=ETC&MobileApp=App&_type=json&arrange=A"
        
        try:
            res = requests.get(url, timeout=15)
            raw_text = res.text.strip()
            
            st.subheader("응답 결과")
            if not raw_text.startswith('{'):
                st.error(f"서버 에러 발생 [HTTP {res.status_code}]\n\n{raw_text[:500]}")
            else:
                st.success("✅ 3번 사진 통신 성공!")
                items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
                if isinstance(items, dict): items = [items]
                
                df = pd.DataFrame(items)
                st.dataframe(df, use_container_width=True)
                
                with st.expander("원본 JSON 데이터 보기"):
                    st.json(items)
        except Exception as e:
            st.error(f"파이썬 통신 에러: {e}")
