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
# 1. 사이드바 (스마트 시장 선택)
# ==========================================
with st.sidebar:
    st.header("⚙️ 분석 설정")
    
    market = st.radio("🌍 시장 선택", ["미국 주식 (US)", "한국 주식 (KR)"])
    
    if market == "미국 주식 (US)":
        search_input = st.text_input("종목 코드 (예: INTC, AAPL, QQQ)", value="INTC").upper()
        currency = "$"
    else:
        search_input = st.text_input("종목번호 6자리 (예: 삼성전자 005930, 에코프로 086520)", value="005930")
        currency = "₩"

    target_mdd = st.number_input("목표 분석 하락률 (%)", min_value=-90.0, max_value=-5.0, value=-50.0, step=5.0)
    buffer = st.slider("하락률 오차 범위 (±%)", min_value=1.0, max_value=10.0, value=5.0, step=1.0)
    
    st.info(f"💡 해석: 과거 역사적 고점 대비 **{target_mdd - buffer}% ~ {target_mdd + buffer}%** 사이로 하락했던 구간들의 회복일만 쏙 뽑아서 평균을 냅니다.")

# ==========================================
# 2. 데이터 수집 및 MDD 알고리즘
# ==========================================
if search_input:
    with st.spinner(f"'{search_input}' 주가 데이터 탐색 및 기업 정보 분석 중... 🕵️‍♂️"):
        
        # 💡 [핵심] 실제 야후 파이낸스 티커 확정 로직
        actual_ticker = search_input
        if market == "한국 주식 (KR)":
            actual_ticker = f"{search_input}.KS"
            data = yf.download(actual_ticker, period="max", progress=False)
            if data.empty:
                actual_ticker = f"{search_input}.KQ"
                data = yf.download(actual_ticker, period="max", progress=False)
        else:
            data = yf.download(actual_ticker, period="max", progress=False)
        
        if data.empty:
            st.error("데이터를 불러오지 못했습니다. 종목 코드(번호)를 다시 확인해 주세요.")
        else:
            # 💡 [신규] 공식 기업명(shortName) 가져오기
            try:
                ticker_obj = yf.Ticker(actual_ticker)
                company_name = ticker_obj.info.get('shortName', search_input)
            except:
                company_name = search_input
                
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
            # 💡 [업데이트] 시원하게 보이도록 기업명을 위로 올리고, 메트릭은 4칸으로 원상복구!
            st.subheader(f"🏢 분석 종목 : **{company_name}** ({actual_ticker})")
            
            col1, col2, col3, col4 = st.columns(4)
            if currency == "₩":
                col1.metric(label="현재가", value=f"{currency}{int(current_price):,}")
            else:
                col1.metric(label="현재가", value=f"{currency}{current_price:.2f}")
                
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
                    
                    if currency == "₩":
                        price_str = f"{currency}{int(target_p):,}"
                    else:
                        price_str = f"{currency}{target_p:.2f}"
                        
                    target_data.append({
                        "목표 하락률": f"{lvl}%",
                        "진입 타겟 단가": price_str,
                        "현재 상태": status
                    })
                
                target_df = pd.DataFrame(target_data)
                
                def highlight_target_row(row):
                    status_text = row['현재 상태']
                    if "진입 타겟" in status_text or "진입 시작" in status_text:
                        return ['background-color: #39ff14; color: black; font-weight: bold;'] * len(row)
                    return [''] * len(row)

                st.dataframe(target_df.style.apply(highlight_target_row, axis=1), use_container_width=True, hide_index=True)
                
                if currency == "₩":
                    st.info(f"💡 현재 일별 최고점(ATH)은 **{currency}{int(current_peak):,}** 입니다. 감정을 배제하고 형광 초록색 타겟 구역이 올 때만 기계적으로 매수하세요.")
                else:
                    st.info(f"💡 현재 일별 최고점(ATH)은 **{currency}{current_peak:.2f}** 입니다. 감정을 배제하고 형광 초록색 타겟 구역이 올 때만 기계적으로 매수하세요.")

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

            # ==========================================
            # 5. 앤트리치 AI 코멘터리 (인사이트 요약)
            # ==========================================
            st.divider()
            st.subheader("🤖 앤트리치 퀀트 AI 리포트")
            
            if current_dd_pct < (overall_max_mdd + 2): 
                diag_msg = f"🚨 **상태 진단:** 현재 하락률({current_dd_pct:.2f}%)이 역대 최악의 폭락 수준에 근접하거나 이미 갱신했습니다! 역사상 경험해 보지 못한 엄청난 바닥권에 위치해 있습니다."
            elif current_dd_pct < -30:
                diag_msg = f"📉 **상태 진단:** 현재 하락률({current_dd_pct:.2f}%)로 보아 꽤 깊은 침체기에 머물고 있습니다. 섣부른 몰빵보다는 원칙적인 분할 접근이 필요합니다."
            else:
                diag_msg = f"📊 **상태 진단:** 현재 고점 대비 {current_dd_pct:.2f}% 하락 중입니다. 주식 시장에서 흔히 겪을 수 있는 일상적인 조정 구간입니다."

            active_buy_signals = [d for d in target_data if "진입 시작" in d['현재 상태']]
            if len(active_buy_signals) > 0:
                action_msg = f"🔥 **행동 지침:** 총 **{len(active_buy_signals)}개의 타겟 구간에서 '진입 시작(초록불)'**이 켜졌습니다! 지금 사면 과거 75% 이상의 날들보다 싼, 압도적으로 유리한 가격입니다. 멘탈을 꽉 잡고 기계적인 분할 매수를 실행할 완벽한 타이밍입니다."
            else:
                action_msg = f"⏳ **행동 지침:** 아직 앤트리치 기준의 매수 메리트(75% 이상)를 충족하는 초록불이 켜지지 않았습니다. 뇌동매매를 멈추고 현금을 아끼며 지정가만 걸어두세요."

            lower_bound = target_mdd - buffer
            upper_bound = target_mdd + buffer
            
            if not periods_df.empty:
                target_periods = periods_df[(periods_df['최대 낙폭(%)'] >= lower_bound) & (periods_df['최대 낙폭(%)'] <= upper_bound)]
                if not target_periods.empty:
                    avg_recovery = int(target_periods['회복 소요일(일)'].mean())
                    time_msg = f"⏱️ **멘탈 관리:** 과거 통계상 선택하신 하락 구간에서 본전을 회복하는 데 평균 **{format_days_to_ym(avg_recovery)}**이 소요되었습니다. 최소 이 기간을 버틸 수 있는 여윳돈으로 긴 호흡의 물타기 플랜을 세우세요."
                else:
                    time_msg = f"⏱️ **멘탈 관리:** 현재 선택하신 {lower_bound}% ~ {upper_bound}% 하락 구간에 대한 과거 회복 완료 데이터가 없습니다. 역대급 침체이므로 매우 보수적인 접근이 필요합니다."
            else:
                time_msg = "⏱️ **멘탈 관리:** 회복 데이터가 충분하지 않습니다."

            st.info(f"{diag_msg}\n\n{action_msg}\n\n{time_msg}")

            # 최근 차트
            st.subheader("📈 최근 5년 주가 흐름 및 전고점")
            chart_df = df.tail(252 * 5)[['Close', 'Peak']]
            chart_df.columns = ['현재가', '전고점(본전)']
            st.line_chart(chart_df)
