import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# 0. 페이지 세팅
# ==========================================
st.set_page_config(page_title="앤트리치 MDD 회복일 계산기", page_icon="🛡️", layout="wide")

st.title("🛡️ 앤트리치 MDD & 평균 회복일 스캐너")
st.write("과거 데이터를 분석하여, 특정 하락장에서 멘탈을 지키고 분할 매수 플랜을 세우기 위한 '평균 회복 기간'을 정확히 계산합니다.")
st.divider()

# ==========================================
# 1. 사이드바 (종목 및 하락률 설정)
# ==========================================
with st.sidebar:
    st.header("⚙️ 분석 설정")
    ticker = st.text_input("종목 코드 입력 (예: INTC, AAPL, MSFT, ^GSPC)", value="INTC").upper()
    target_mdd = st.number_input("목표 분석 하락률 (%)", min_value=-90.0, max_value=-5.0, value=-50.0, step=5.0)
    buffer = st.slider("하락률 오차 범위 (±%)", min_value=1.0, max_value=10.0, value=5.0, step=1.0)
    
    st.info(f"💡 해석: 과거 고점 대비 **{target_mdd - buffer}% ~ {target_mdd + buffer}%** 사이로 하락했던 구간들의 회복일만 쏙 뽑아서 평균을 냅니다.")

# ==========================================
# 2. 데이터 수집 및 MDD 알고리즘
# ==========================================
if ticker:
    with st.spinner(f"'{ticker}' 과거 수십 년 치 주가 데이터 및 계곡 깊이 탐색 중... 🕵️‍♂️"):
        # 야후 파이낸스 데이터 다운로드 (최대 기간)
        data = yf.download(ticker, period="max", progress=False)
        
        if data.empty:
            st.error("데이터를 불러오지 못했습니다. 종목 코드를 다시 확인해 주세요.")
        else:
            # 다중 인덱스 제거 (yfinance 최신 버전 호환성)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
                
            df = data[['Close']].copy()
            df = df.dropna()
            
            # 1. 최고가(Peak) 및 일일 Drawdown 계산
            df['Peak'] = df['Close'].cummax()
            df['Drawdown'] = (df['Close'] - df['Peak']) / df['Peak']
            
            # 2. 전고점(Peak) 갱신일 찾기 (Drawdown이 0인 날)
            peak_dates = df[df['Drawdown'] == 0].index
            
            # 3. 하락장(Underwater) 구간별 데이터 추출
            periods = []
            for i in range(len(peak_dates) - 1):
                start_date = peak_dates[i]
                end_date = peak_dates[i+1]
                
                # 고점과 다음 고점 사이의 구간 추출
                subset = df.loc[start_date:end_date]
                
                # 구간이 1일 이상 차이 날 때 (즉, 가격이 떨어졌다가 회복한 구간)
                duration_days = (end_date - start_date).days
                
                if duration_days > 0:
                    max_drop = subset['Drawdown'].min() * 100 # %로 변환
                    periods.append({
                        '하락 시작일': start_date.strftime('%Y-%m-%d'),
                        '회복 완료일': end_date.strftime('%Y-%m-%d'),
                        '최대 낙폭(%)': round(max_drop, 2),
                        '회복 소요일(일)': duration_days
                    })
            
            # 현재 진행 중인 미회복 하락장 계산
            last_peak = peak_dates[-1]
            current_subset = df.loc[last_peak:]
            current_max_drop = current_subset['Drawdown'].min() * 100
            current_duration = (df.index[-1] - last_peak).days
            
            # ==========================================
            # 3. 목표 하락률 필터링 및 통계
            # ==========================================
            periods_df = pd.DataFrame(periods)
            
            # 타겟 범위 설정
            lower_bound = target_mdd - buffer
            upper_bound = target_mdd + buffer
            
            if not periods_df.empty:
                # 조건에 맞는 하락장만 필터링
                target_periods = periods_df[
                    (periods_df['최대 낙폭(%)'] >= lower_bound) & 
                    (periods_df['최대 낙폭(%)'] <= upper_bound)
                ]
                
                overall_max_mdd = periods_df['최대 낙폭(%)'].min()
                overall_max_days = periods_df['회복 소요일(일)'].max()
                
                # UI 출력 (대시보드)
                col1, col2, col3 = st.columns(3)
                
                col1.metric(label="역대 최악의 폭락 (MDD)", value=f"{overall_max_mdd:.2f}%")
                col2.metric(label="역대 최장 회복기간 (MAX)", value=f"{overall_max_days}일")
                col3.metric(label="현재 하락 진행률 (고점 대비)", value=f"{current_max_drop:.2f}%", delta=f"{current_duration}일째 물림", delta_color="inverse")
                
                st.divider()
                st.subheader(f"🎯 [{target_mdd}%] 수준 폭락장 분석 결과")
                
                if not target_periods.empty:
                    avg_recovery = int(target_periods['회복 소요일(일)'].mean())
                    max_recovery_in_target = int(target_periods['회복 소요일(일)'].max())
                    event_count = len(target_periods)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric(label=f"조건 부합 횟수", value=f"{event_count}회")
                    c2.metric(label=f"평균 회복일", value=f"{avg_recovery}일")
                    c3.metric(label=f"해당 구간 최장 회복일", value=f"{max_recovery_in_target}일")
                    
                    st.write(f"💡 **앤트리치 퀀트 전략:** 과거 통계상 이 종목이 **{lower_bound}% ~ {upper_bound}%** 사이로 하락했을 때, 전고점을 탈환하는 데 평균적으로 **{avg_recovery}일**이 걸렸습니다. 자금 투입 시 이 기간을 염두에 두고 분할 매수 호흡을 조절하세요!")
                    
                    with st.expander("📊 상세 회복 기록 데이터 보기"):
                        st.dataframe(target_periods, use_container_width=True)
                else:
                    st.warning(f"과거 역사상 {lower_bound}% ~ {upper_bound}% 수준으로 하락한 후 회복을 완료한 데이터가 없습니다.")
                    
                # 간단한 차트 (최근 5년)
                st.subheader("📈 최근 5년 주가 흐름 및 전고점")
                chart_df = df.tail(252 * 5)[['Close', 'Peak']]
                chart_df.columns = ['현재가', '전고점(본전)']
                st.line_chart(chart_df)
                
            else:
                st.info("충분한 데이터가 없습니다.")
