import pandas as pd
import streamlit as st

# =========================================================
# 1. 포트폴리오 설정 (사용자 지정 비중 & 기본 기대수익률)
# =========================================================

ETF_CONFIG = {
    "연금저축": [
        {"key": "p_sp500", "name": "TIGER 미국S&P500", "weight": 0.25, "annual_amount": 1_500_000, "default_return": 9.0},
        {"key": "p_nasdaq", "name": "KODEX 미국나스닥100", "weight": 0.25, "annual_amount": 1_500_000,
         "default_return": 11.0},
        {"key": "p_dividend", "name": "KODEX 미국배당다우존스", "weight": 0.50, "annual_amount": 3_000_000,
         "default_return": 8.0},
    ],
    "IRP": [
        {"key": "i_high_div", "name": "KODEX 주주환원고배당주", "weight": 0.30, "annual_amount": 900_000,
         "default_return": 7.5},
        {"key": "i_cover_call", "name": "KODEX 200타겟위클리커버드콜", "weight": 0.40, "annual_amount": 1_200_000,
         "default_return": 6.5},
        {"key": "i_bond", "name": "KODEX 단기채권PLUS", "weight": 0.30, "annual_amount": 900_000, "default_return": 3.5},
    ],
}


def money_sim(value: float) -> str:
    """통화 단위 표현 헬퍼 함수"""
    val = int(value)
    if abs(val) >= 100_000_000:
        eok = val // 100_000_000
        man = (val % 100_000_000) // 10_000
        return f"{eok:,}억 {man:,}만원" if man > 0 else f"{eok:,}억원"
    elif abs(val) >= 10_000:
        return f"{val // 10_000:,}만원"
    return f"{val:,}원"


# =========================================================
# 2. 시뮬레이션 계산 로직
# =========================================================

def calculate_simulation(
        initial_asset: int,
        annual_pension_deposit: int,
        annual_irp_deposit: int,
        invest_years: int,
        expected_returns: dict,
        tax_credit_rate: float,
        reinvest_tax_credit: bool,
):
    # 1) 계좌별 가중평균 기대수익률 산출
    pension_return = sum(
        cfg["weight"] * expected_returns.get(cfg["key"], cfg["default_return"])
        for cfg in ETF_CONFIG["연금저축"]
    )
    irp_return = sum(
        cfg["weight"] * expected_returns.get(cfg["key"], cfg["default_return"])
        for cfg in ETF_CONFIG["IRP"]
    )

    total_deposit = annual_pension_deposit + annual_irp_deposit

    # 통합 가중평균 수익률
    if total_deposit > 0:
        overall_return = (
                                 (annual_pension_deposit * pension_return) + (annual_irp_deposit * irp_return)
                         ) / total_deposit
    else:
        overall_return = (pension_return + irp_return) / 2.0

    # 2) 연도별 복리 계산
    records = []
    current_asset = float(initial_asset)
    total_principal = float(initial_asset)
    total_tax_reinvested = 0.0

    rate_decimal = overall_return / 100.0

    for year in range(1, invest_years + 1):
        # 세액공제 대상액 (연금저축 최대 600만 + IRP 포함 최대 900만)
        eligible_tax_deposit = min(annual_pension_deposit, 6_000_000) + min(
            annual_irp_deposit, max(0, 9_000_000 - min(annual_pension_deposit, 6_000_000))
        )
        tax_refund = eligible_tax_deposit * (tax_credit_rate / 100.0)

        year_deposit = total_deposit
        reinvest_amount = tax_refund if reinvest_tax_credit else 0.0

        total_principal += year_deposit
        total_tax_reinvested += reinvest_amount

        # 운용 자산 = (전년도 자산 + 당해 원금 납입 + 세액공제 환급 재투자금) * (1 + 수익률)
        invested_base = current_asset + year_deposit + reinvest_amount
        investment_profit = invested_base * rate_decimal
        current_asset = invested_base + investment_profit

        records.append({
            "경과년수": f"{year}년차",
            "총 누적자산": int(current_asset),
            "누적 원금": int(total_principal),
            "누적 투자수익": int(current_asset - total_principal - total_tax_reinvested),
            "누적 세액환급 재투자": int(total_tax_reinvested),
            "당해 세액공제 환급액": int(tax_refund),
        })

    df_result = pd.DataFrame(records)
    return df_result, overall_return, pension_return, irp_return


# =========================================================
# 3. Streamlit UI 메인 화면
# =========================================================

def show_asset_simulation(user_id=None, cookies=None):
    st.title("📈 연금 자산 성장 시뮬레이터 (5년 플랜)")
    st.caption("연금저축(600만원) + IRP(300만원) 총 900만원 납입 포트폴리오 추정")

    st.divider()

    # --- 사이드바 설정 영역 ---
    st.sidebar.header("⚙️ 시뮬레이션 설정")

    initial_asset = st.sidebar.number_input(
        "현재 보유 자산 총액 (원)", min_value=0, value=0, step=1_000_000, format="%d"
    )

    st.sidebar.subheader("💵 연간 납입 목표액")
    annual_pension = st.sidebar.number_input(
        "연금저축 연 납입액", min_value=0, max_value=6_000_000, value=6_000_000, step=500_000
    )
    annual_irp = st.sidebar.number_input(
        "IRP 연 납입액", min_value=0, max_value=3_000_000, value=3_000_000, step=500_000
    )

    invest_years = st.sidebar.slider("투자 기간 (년)", min_value=1, max_value=30, value=5, step=1)

    st.sidebar.subheader("🎁 세액공제 설정")
    tax_rate_option = st.sidebar.radio(
        "총급여 기준 세액공제율",
        options=[16.5, 13.2],
        format_func=lambda x: f"{x}% (총급여 {'5,500만원 이하' if x == 16.5 else '5,500만원 초과'})",
    )
    reinvest_tax = st.sidebar.checkbox("세액공제 환급금 매년 재투자하기", value=True)

    # --- 포트폴리오 가중치 및 기대수익률 설정 ---
    with st.expander("📊 종목별 기대 수익률 조정 (클릭하여 개별 수정 가능)", expanded=True):
        col_p, col_i = st.columns(2)

        expected_returns = {}
        with col_p:
            st.markdown("### 🟢 연금저축 계좌 (연 600만 원)")
            for cfg in ETF_CONFIG["연금저축"]:
                st.write(f"• **{cfg['name']}** ({int(cfg['weight'] * 100)}% / 연 {money_sim(cfg['annual_amount'])})")
                expected_returns[cfg["key"]] = st.number_input(
                    f"{cfg['name']} 기대수익률(%)",
                    min_value=-10.0,
                    max_value=30.0,
                    value=cfg["default_return"],
                    step=0.5,
                    key=f"ret_{cfg['key']}",
                )

        with col_i:
            st.markdown("### 🔵 IRP 계좌 (연 300만 원)")
            for cfg in ETF_CONFIG["IRP"]:
                st.write(f"• **{cfg['name']}** ({int(cfg['weight'] * 100)}% / 연 {money_sim(cfg['annual_amount'])})")
                expected_returns[cfg["key"]] = st.number_input(
                    f"{cfg['name']} 기대수익률(%)",
                    min_value=-10.0,
                    max_value=30.0,
                    value=cfg["default_return"],
                    step=0.5,
                    key=f"ret_{cfg['key']}",
                )

    # --- 연산 진행 ---
    df_result, overall_ret, pension_ret, irp_ret = calculate_simulation(
        initial_asset=initial_asset,
        annual_pension_deposit=annual_pension,
        annual_irp_deposit=annual_irp,
        invest_years=invest_years,
        expected_returns=expected_returns,
        tax_credit_rate=tax_rate_option,
        reinvest_tax_credit=reinvest_tax,
    )

    final_row = df_result.iloc[-1]
    final_asset = final_row["총 누적자산"]
    final_principal = final_row["누적 원금"]
    final_profit = final_row["누적 투자수익"]
    final_tax_reinvested = final_row["누적 세액환급 재투자"]
    annual_tax_refund = (annual_pension + annual_irp) * (tax_rate_option / 100.0)

    # --- 요약 카드 출력 ---
    st.subheader(f"🎯 {invest_years}년 납입 후 시뮬레이션 결과 요약")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("최종 예상 총자산", money_sim(final_asset))
    m2.metric("총 투입 원금", money_sim(final_principal))
    m3.metric("순 투자 수익", money_sim(final_profit))
    m4.metric("통합 가중평균 수익률", f"{overall_ret:.2f}% / 년")

    st.info(
        f"💡 **포트폴리오 수익률 분석**\n"
        f"* 연금저축 가중평균 수익률: **{pension_ret:.2f}%** | IRP 가중평균 수익률: **{irp_ret:.2f}%**\n"
        f"* 매년 발생하는 세액공제 환급액: **{money_sim(annual_tax_refund)}** "
        f"({invest_years}년간 총 {money_sim(final_tax_reinvested)} 재투자 반영됨)"
    )

    st.divider()

    # --- 자산 성장 시각화 차트 ---
    st.subheader("📈 연도별 자산 누적 추이")
    chart_data = df_result.set_index("경과년수")[
        ["누적 원금", "누적 세액환급 재투자", "누적 투자수익"]
    ]
    st.bar_chart(chart_data, use_container_width=True)

    st.divider()

    # --- 연도별 상세 데이터표 ---
    with st.expander("📋 연도별 상세 데이터 확인", expanded=True):
        formatted_df = df_result.copy()
        for col in ["총 누적자산", "누적 원금", "누적 투자수익", "누적 세액환급 재투자", "당해 세액공제 환급액"]:
            formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,}원")
        st.dataframe(formatted_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    show_asset_simulation()