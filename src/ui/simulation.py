import pandas as pd
import plotly.express as px
import streamlit as st

from src.utils.simulator import run_retirement_simulation


def money(value):
    return f"{int(value):,}원"


def show_simulation_dashboard(user_id=None, cookies=None):
    st.title("📊 자산 성장 및 은퇴 시뮬레이션")
    st.caption("복리 효과와 물가상승률을 반영하여 은퇴 시점 자산과 노후 자산 유지 기간을 예측합니다.")

    st.divider()

    # =========================================================
    # 1. 입력 파라미터 설정 (사이드 바 또는 메인 2컬럼)
    # =========================================================
    st.subheader("⚙️ 시뮬레이션 변수 설정")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("##### 👤 연령 조건")
        current_age = st.number_input("현재 연령", min_value=20, max_value=70, value=35)
        retirement_age = st.number_input("목표 은퇴 연령", min_value=current_age + 1, max_value=80, value=60)
        life_expectancy = st.number_input("기대 수명", min_value=retirement_age + 1, max_value=100, value=85)

    with col2:
        st.markdown("##### 💵 자산 및 납입금")
        current_asset = st.number_input("현재 보유 자산 (원)", min_value=0, value=20_000_000, step=1_000_000, format="%d")
        monthly_contribution = st.number_input("월 납입금 (원)", min_value=0, value=750_000, step=50_000, format="%d")
        target_monthly_withdrawal = st.number_input("은퇴 후 희망 월 수령액 (원)", min_value=0, value=2_500_000, step=10_000,
                                                    format="%d")

    with col3:
        st.markdown("##### 📈 수익률 및 물가상승률")
        return_acc = st.slider("축적기 연 수익률 (%)", min_value=1.0, max_value=15.0, value=7.0, step=0.5) / 100.0
        return_ret = st.slider("수령기 연 수익률 (%)", min_value=1.0, max_value=10.0, value=4.0, step=0.5) / 100.0
        inflation = st.slider("예상 연 물가상승률 (%)", min_value=0.0, max_value=6.0, value=2.5, step=0.1) / 100.0

    st.divider()

    # =========================================================
    # 2. 시뮬레이션 연산 수행
    # =========================================================
    sim_result = run_retirement_simulation(
        current_age=current_age,
        retirement_age=retirement_age,
        life_expectancy=life_expectancy,
        current_asset=current_asset,
        monthly_contribution=monthly_contribution,
        annual_return_accumulation=return_acc,
        annual_return_retirement=return_ret,
        annual_inflation_rate=inflation,
        target_monthly_withdrawal=target_monthly_withdrawal,
    )

    df = sim_result["df"]
    depleted_age = sim_result["depleted_age"]

    # =========================================================
    # 3. 주요 KPI 결과 카드
    # =========================================================
    st.subheader("🎯 시뮬레이션 요약 결과")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.metric("은퇴 시점 명목 자산", money(sim_result["asset_at_retirement"]))
    with kpi2:
        st.metric("은퇴 시점 실질 자산", money(sim_result["real_asset_at_retirement"]), help="물가상승률을 감안한 현재 가치 기준")
    with kpi3:
        st.metric("총 투입 원금", money(sim_result["total_principal_at_retirement"]))
    with kpi4:
        if depleted_age:
            st.metric("자산 고갈 예상 연령", f"{depleted_age}세", delta=f"{depleted_age - life_expectancy}년 부족",
                      delta_color="inverse")
        else:
            st.metric("자산 고갈 여부", "✅ 안전 (자산 충분)", delta=f"{life_expectancy}세까지 유지")

    if depleted_age:
        st.error(
            f"⚠️ **자산 고갈 경고:** 현재 희망 수령액({money(target_monthly_withdrawal)})을 유지할 경우 "
            f"**{depleted_age}세**에 자산이 고갈됩니다. 월 납입금을 늘리거나 은퇴 후 희망 수령액을 조정하세요."
        )

    # =========================================================
    # 4. 차트 시각화 (Plotly)
    # =========================================================
    st.subheader("📈 자산 성장 및 인출 트렌드")

    # Plotly 라인 차트 생성
    fig = px.line(
        df,
        x="연령",
        y=["명목 자산", "실질 자산(현재가치)", "총 투입 원금"],
        labels={"value": "자산 평가액 (원)", "variable": "자산 구분"},
        title=f"연령별 자산 추이 ({current_age}세 ~ {life_expectancy}세)",
    )

    # 은퇴 시점 세로 수직선 추가
    fig.add_vline(x=retirement_age, line_dash="dash", line_color="orange", annotation_text="은퇴 시점")

    fig.update_layout(
        hovermode="x unified",
        yaxis_tickformat=",d",
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

    # =========================================================
    # 5. 연도별 상세 데이터 테이블
    # =========================================================
    with st.expander("📄 연령별 상세 시뮬레이션 데이터 보기"):
        st.dataframe(
            df.style.format({
                "총 투입 원금": "{:,}원",
                "명목 자산": "{:,}원",
                "실질 자산(현재가치)": "{:,}원",
            }),
            use_container_width=True,
            hide_index=True,
        )