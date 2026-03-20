import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# 0. 페이지 세팅 및 도우미 함수
# ==========================================
st.set_page_config(page_title="앤트리치 MDD 회복일 계산기", page_icon="🛡️", layout="wide")

def format_days_to_ym(days):
    if pd.isna(days) or days == 0:
        return "0일"
    days = int(days)
    years = days // 365
    months = (days % 365) // 30
    
    if years > 0 and months > 0:
        return f"{days}일 ({years}년 {months}개월)"
    elif years > 0 and months == 0:
        return f"{days}일 ({years}년)"
    elif years == 0 and months > 0:
        return f"{days}일 ({months}개월)"
    else:
        return f"{days}일"

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
    
    st.info(f"💡 해석: 과거 역사적 고점 대비 **{target_mdd - buffer}% ~ {target_mdd + buffer}%** 사이로 하락했던 구간들의 회복일만 쏙 뽑아서 평균을 냅니다.")

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
            col2.metric(label="전고점 대비 하락률 (MDD)", value=f"{current_dd_pct:.2f}%", delta=f"전고점({last_peak.strftime('%y.%m.%d')}) 이후 {format_days_to_ym(current_duration)}째", delta_color="inverse")
            col3.metric(label="역대 최악의 폭락 (MAX MDD)", value=f"{overall_max_mdd:.2f}%")
            col4.metric(label="역대 최장 회복기간", value=format_days_to_ym(overall_max_days))
            
            st.divider()
            
            # ==========================================
            # 4. 매수 타점 (기준가) & 퍼센타일 표
            # ==========================================
            st.subheader("🎯 기계적 분할 매수 타점 & 메리트 분석")
            
            total_days = len(df)
            c1, c2 = st.columns([1, 1])
            
            with c1:
                st.markdown("##### 📍 목표 하락률별 진입 단가")
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
                
                target_df = pd.DataFrame(target_data)
                
                # 💡 [신규] 현재가가 목표 단가 이하일 때(도달 시) 해당 행을 형광 초록으로 칠하는 함수
                def highlight_target_row(row):
                    try:
                        val = float(row['진입 타겟 단가'].replace('$', '').replace(',', ''))
                        if current_price <= val:
                            return ['background-color: #39ff14; color: black; font-weight: bold;'] * len(row)
                    except:
                        pass
                    return [''] * len(row)

                st.dataframe(target_df.style.apply(highlight_target_row, axis=1), use_container_width=True, hide_index=True)
                st.info(f"💡 현재 일별 최고점(ATH)은 **${current_peak:.2f}** 입니다. 감정을 배제하고 형광 초록색(도달) 불이 들어왔을 때만 대응하세요.")

            with c2:
                st.markdown("##### 📊 하락 깊이별 매수 메리트 (퍼센타일)")
                mdd_bins = np.arange(0, -95, -5)
                percentile_data = []
                
                for mdd_val in mdd_bins:
                    better_days = len(df[df['Drawdown'] >= (mdd_val / 100)])
                    pct = (better_days / total_days) * 100
                    percentile_data.append({
                        "MDD 깊이": f"{mdd_val}%",
                        "매수 메리트 (역사적 하위%)": f"{pct:.1f}%"
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
                
                st.dataframe(pct_df.style.map(highlight_pct, subset=['매수 메리트 (역사적 하위%)']), use_container_width=True, hide_index=True)

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
                    c2.metric(label=f"평균 회복일", value=format_days_to_ym(avg_recovery))
                    c3.metric(label=f"해당 구간 최장 회복일", value=format_days_to_ym(max_recovery_in_target))
                    
                    st.write(f"💡 **앤트리치 퀀트 전략:** 통계상 **{lower_bound}% ~ {upper_bound}%** 사이로 하락했을 때, 전고점 탈환에 평균 **{format_days_to_ym(avg_recovery)}**이 걸렸습니다. 자금 투입 시 이 기간을 염두에 두고 호흡을 조절하세요!")
                else:
                    st.warning(f"역사상 {lower_bound}% ~ {upper_bound}% 수준의 하락 후 회복된 기록이 없습니다.")
            
            # 최근 차트
            st.subheader("📈 최근 5년 주가 흐름 및 전고점")
            chart_df = df.tail(252 * 5)[['Close', 'Peak']]
            chart_df.columns = ['현재가', '전고점(본전)']
            st.line_chart(chart_df)
