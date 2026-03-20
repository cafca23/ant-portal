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
# 1. 사이드바 (종목, 기간 및 하락률 설정)
# ==========================================
with st.sidebar:
    st.header("⚙️ 분석 설정")
    ticker = st.text_input("종목 코드 입력 (예: INTC, AAPL, MSFT, ^GSPC)", value="INTC").upper()
    
    # [신규] 분석 기간 선택 옵션 추가
    st.subheader("🗓️ 전고점 기준 (기간)")
    period_dict = {
        "전체 기간 (역사적 최고점)": "max",
        "최근 10년": "10y",
        "최근 5년": "5y",
        "최근 3년": "3y",
        "최근 1년 (52주 최고점)": "1y"
    }
    selected_period_label = st.selectbox("어느 기간의 고점을 기준으로 할까요?", list(period_dict.keys()))
    selected_period = period_dict[selected_period_label]
    
    st.subheader("🎯 하락률 타겟")
    target_mdd = st.number_input("목표 분석 하락률 (%)", min_value=-90.0, max_value=-5.0, value=-50.0, step=5.0)
    buffer = st.slider("하락률 오차 범위 (±%)", min_value=1.0, max_value=10.0, value=5.0, step=1.0)
    
    st.info(f"💡 해석: 선택하신 **[{selected_period_label}]** 내에서 최고점 대비 **{target_mdd - buffer}% ~ {target_mdd + buffer}%** 사이로 하락했던 구간을 집중 분석합니다.")

# ==========================================
# 2. 데이터 수집 및 MDD 알고리즘
# ==========================================
if ticker:
    with st.spinner(f"'{ticker}' 주가 데이터 탐색 및 퀀트 분석 중... 🕵️‍♂️"):
        # 사용자가 선택한 기간(selected_period)으로 데이터 다운로드
        data = yf.download(ticker, period=selected_period, progress=False)
        
        if data.empty:
            st.error("데이터를 불러오지 못했습니다. 종목 코드나 기간을 다시 확인해 주세요.")
        else:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
                
            df = data[['Close']].copy()
            df = df.dropna()
            
            # 최고가 및 MDD 계산
            df['Peak'] = df['Close'].cummax()
            df['Drawdown'] = (df['Close'] - df['Peak']) / df['Peak']
            
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
            # [업데이트] 날짜가 직관적으로 보이도록 수정
            col2.metric(label="현재 하락 진행률 (MDD)", value=f"{current_dd_pct:.2f}%", delta=f"고점({last_peak.strftime('%y.%m.%d')}) 이후 {current_duration}일째", delta_color="inverse")
            col3.metric(label=f"기간 내 최악의 폭락 (MAX)", value=f"{overall_max_mdd:.2f}%")
            col4.metric(label="기간 내 최장 회복기간", value=f"{overall_max_days}일")
            
            st.divider()
            
            # ==========================================
            # 4. 매수 타점 (기준가) & 퍼센타일 표
            # ==========================================
            st.subheader("🎯 기계적 분할 매수 타점 & 메리트 분석")
            
            total_days = len(df)
            c1, c2 = st.columns([1, 1])
            
            with c1:
                st.markdown(f"##### 📍 목표 하락률별 진입 단가 ({selected_period_label} 기준)")
                target_levels = np.arange(-20, -85, -5) 
                target_data = []
                
                for lvl in target_levels:
                    target_p = current_peak * (1 + (lvl / 100))
                    
                    better_days = len(df[df['Drawdown'] >= (lvl / 100)])
                    pct = (better_days / total_days) * 100
                    
                    if pct >= 75.0:
                        if current_price <= target_p:
                            status = "🔥 진입 시작 (도달)"
                        else:
                            status = "🎯 진입 타겟 (대기중)"
                    else:
                        if current_price <= target_p:
                            status = "⚠️ 관망 (메리트 부족)"
                        else:
                            status = "⏳ 대기 중"
                    
                    target_data.append({
                        "목표 하락률": f"{lvl}%",
                        "진입 타겟 단가": f"${target_p:.2f}",
                        "현재 상태": status
                    })
                
                st.dataframe(pd.DataFrame(target_data), use_container_width=True, hide_index=True)
                st.info(f"💡 선택하신 기간 내 최고점은 **${current_peak:.2f}** 입니다. 감정을 배제하고 기계적으로 대응하세요.")

            with c2:
                st.markdown("##### 📊 하락 깊이별 매수 메리트 (퍼센타일)")
                mdd_bins = np.arange(0, -95, -5)
                percentile_data = []
                
                for mdd_val in mdd_bins:
                    better_days = len(df[df['Drawdown'] >= (mdd_val / 100)])
                    pct = (better_days / total_days) * 100
                    percentile_data.append({
                        "MDD 깊이": f"{mdd_val}%",
                        "매수 메리트 (선택 기간 내 하위%)": f"{pct:.1f}%"
                    })
                
                pct_df = pd.DataFrame(percentile_data)
                
                def highlight_pct(val):
                    try:
                        num = float(val.replace('%', ''))
                        if num >= 75.0:
                            return 'background-color: #fca311; color: black; font-weight: bold;'
                        elif num >= 50.0:
                            return 'background-color: #ffecd1; color: black;'
                    except: pass
                    return ''
                
                st.dataframe(pct_df.style.map(highlight_pct, subset=['매수 메리트 (선택 기간 내 하위%)']), use_container_width=True, hide_index=True)

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
                    
                    st.write(f"💡 **앤트리치 퀀트 전략:** 통계상 **{lower_bound}% ~ {upper_bound}%** 사이로 하락했을 때, 전고점 탈환에 평균 **{avg_recovery}일**이 걸렸습니다.")
                else:
                    st.warning(f"선택하신 기간 내에는 {lower_bound}% ~ {upper_bound}% 수준의 하락 후 회복된 기록이 없습니다.")
            
            # 최근 차트
            st.subheader(f"📈 {selected_period_label} 주가 흐름 및 전고점")
            chart_df = df[['Close', 'Peak']]
            chart_df.columns = ['현재가', '전고점(본전)']
            st.line_chart(chart_df)
