import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# 0. 페이지 세팅
# ==========================================
st.set_page_config(page_title="앤트리치 MDD 회복일 계산기", page_icon="🛡️", layout="wide")

st.title("🛡️ 앤트리치 MDD & 퀀트 분할매수 계산기")
st.write("과거 데이터를 분석하여 하락장 평균 회복 기간을 구하고, 잃지 않는 분할 매수 타점을 시각화합니다.")
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
    with st.spinner(f"'{ticker}' 주가 데이터 탐색 및 퀀트 분석 중... 🕵️‍♂️"):
        data = yf.download(ticker, period="max", progress=False)
        
        if data.empty:
            st.error("데이터를 불러오지 못했습니다. 종목 코드를 다시 확인해 주세요.")
        else:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
                
            df = data[['Close']].copy()
            df = df.dropna()
            
            # 최고가 및 MDD 계산
            df['Peak'] = df['Close'].cummax()
            df['Drawdown'] = (df['Close'] - df['Peak']) / df['Peak']
            
            # 현재 상태 변수
            current_price = df['Close'].iloc[-1]
            current_peak = df['Peak'].iloc[-1]
            current_dd_pct = df['Drawdown'].iloc[-1] * 100
            
            peak_dates = df[df['Drawdown'] == 0].index
            
            periods = []
            for i in range(len(peak_dates) - 1):
                start_date = peak_dates[i]
                end_date = peak_dates[i+1]
                subset = df.loc[start_date:end_date]
                duration_days = (end_date - start_date).days
                
                if duration_days > 0:
                    max_drop = subset['Drawdown'].min() * 100
                    periods.append({
                        '하락 시작일': start_date.strftime('%Y-%m-%d'),
                        '회복 완료일': end_date.strftime('%Y-%m-%d'),
                        '최대 낙폭(%)': round(max_drop, 2),
                        '회복 소요일(일)': duration_days
                    })
            
            last_peak = peak_dates[-1]
            current_duration = (df.index[-1] - last_peak).days
            
            periods_df = pd.DataFrame(periods)
            overall_max_mdd = periods_df['최대 낙폭(%)'].min() if not periods_df.empty else current_dd_pct
            overall_max_days = periods_df['회복 소요일(일)'].max() if not periods_df.empty else 0

            # ==========================================
            # 3. 메인 대시보드 출력
            # ==========================================
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(label="현재가", value=f"${current_price:.2f}")
            col2.metric(label="현재 하락 진행률 (MDD)", value=f"{current_dd_pct:.2f}%", delta=f"{current_duration}일째 물림", delta_color="inverse")
            col3.metric(label="역대 최악의 폭락 (MAX MDD)", value=f"{overall_max_mdd:.2f}%")
            col4.metric(label="역대 최장 회복기간", value=f"{overall_max_days}일")
            
            st.divider()
            
            # ==========================================
            # 4. [신규] 매수 타점 (기준가) & 퍼센타일 표
            # ==========================================
            st.subheader("🎯 기계적 분할 매수 타점 & 메리트 분석")
            
            c1, c2 = st.columns([1, 1])
            
            with c1:
                st.markdown("##### 📍 목표 하락률별 진입 단가")
                target_levels = [-20, -30, -40, -50, -60, -70, -80]
                target_data = []
                for lvl in target_levels:
                    target_p = current_peak * (1 + (lvl / 100))
                    status = "✅ 진입 가능 (도달)" if current_price <= target_p else "⏳ 대기 중"
                    target_data.append({
                        "목표 하락률": f"{lvl}%",
                        "진입 타겟 단가": f"${target_p:.2f}",
                        "현재 상태": status
                    })
                
                st.dataframe(pd.DataFrame(target_data), use_container_width=True, hide_index=True)
                st.info(f"💡 현재 일별 최고점(ATH)은 **${current_peak:.2f}** 입니다. 감정을 배제하고 위 타겟 단가가 올 때만 기계적으로 매수하세요.")

            with c2:
                st.markdown("##### 📊 하락 깊이별 매수 메리트 (퍼센타일)")
                # 백분위수(회복률) 계산 로직
                mdd_bins = np.arange(0, -95, -5)
                percentile_data = []
                total_days = len(df)
                
                for mdd_val in mdd_bins:
                    # 과거에 해당 MDD보다 '덜' 빠졌던 날의 비율
                    better_days = len(df[df['Drawdown'] >= (mdd_val / 100)])
                    pct = (better_days / total_days) * 100
                    percentile_data.append({
                        "MDD 깊이": f"{mdd_val}%",
                        "매수 메리트 (역사적 하위%)": f"{pct:.1f}%"
                    })
                
                pct_df = pd.DataFrame(percentile_data)
                
                # 색상 하이라이트 함수 (50% 연한 노랑, 75% 진한 노랑)
                def highlight_pct(val):
                    try:
                        num = float(val.replace('%', ''))
                        if num >= 75.0:
                            return 'background-color: #fca311; color: black; font-weight: bold;'
                        elif num >= 50.0:
                            return 'background-color: #ffecd1; color: black;'
                    except: pass
                    return ''
                
                st.dataframe(pct_df.style.applymap(highlight_pct, subset=['매수 메리트 (역사적 하위%)']), use_container_width=True, hide_index=True)

            st.divider()

            # ==========================================
            # 5. 기존 평균 회복일 분석
            # ==========================================
            st.subheader(f"⏱️ [{target_mdd}%] 수준 폭락장 평균 회복 기간")
            lower_bound = target_mdd - buffer
            upper_bound = target_mdd + buffer
            
            if not periods_df.empty:
                target_periods = periods_df[
                    (periods_df['최대 낙폭(%)'] >= lower_bound) & 
                    (periods_df['최대 낙폭(%)'] <= upper_bound)
                ]
                
                if not target_periods.empty:
                    avg_recovery = int(target_periods['회복 소요일(일)'].mean())
                    max_recovery_in_target = int(target_periods['회복 소요일(일)'].max())
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric(label=f"조건 부합 횟수", value=f"{len(target_periods)}회")
                    c2.metric(label=f"평균 회복일", value=f"{avg_recovery}일")
                    c3.metric(label=f"해당 구간 최장 회복일", value=f"{max_recovery_in_target}일")
                    
                    st.write(f"💡 **앤트리치 퀀트 전략:** 통계상 **{lower_bound}% ~ {upper_bound}%** 사이로 하락했을 때, 전고점 탈환에 평균 **{avg_recovery}일**이 걸렸습니다. 자금 투입 시 이 기간을 염두에 두고 호흡을 조절하세요!")
                else:
                    st.warning(f"역사상 {lower_bound}% ~ {upper_bound}% 수준의 하락 후 회복된 기록이 없습니다.")
            
            # 최근 차트
            st.subheader("📈 최근 5년 주가 흐름 및 전고점")
            chart_df = df.tail(252 * 5)[['Close', 'Peak']]
            chart_df.columns = ['현재가', '전고점(본전)']
            st.line_chart(chart_df)
