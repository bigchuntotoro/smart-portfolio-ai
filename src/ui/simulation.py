import pandas as pd
import streamlit as st

# =========================================================
# 1. 포트폴리오 설정 (기본 기대수익률 시나리오별 정의)
# =========================================================

ETF_CONFIG = {
    "연금저축": [
        {
            "key": "p_sp500",
            "name": "TIGER 미국S&P500",
            "weight": 0.25,
            "annual_amount": 1_500_000,
            "returns": {"보수적": 6.0, "중립적": 8.0, "공격적": 10.0},
        },
        {
            "key": "p_nasdaq",
            "name": "KODEX 미국나스닥100",
            "weight": 0.25,
            "annual_amount": 1_500_000,
            "returns": {"보수적": 7.0, "중립적": 9.5, "공격적": 12.0},
        },
        {
            "key": "p_dividend",
            "name": "KODEX 미국배당다우존스",
            "weight": 0.50,
            "annual_amount": 3_000_000,
            "returns": {"보수적": 5.5, "중립적": 7.5, "공격적": 9.0},
        },
    ],
    "IRP": [
        {
            "key": "i_high_div",
            "name": "KODEX 주주환원고배당주",
            "weight": 0.30,
            "annual_amount": 900_000,
            "returns": {"보수적": 4.0, "중립적": 5.5, "공격적": 7.0},
        },
        {
            "key": "i_cover_call",
            "name": "KODEX 200타겟위클리커버드콜",
            "weight": 0.40,
            "annual_amount": 1_200_000,
            "returns": {"보수적": 3.5, "중립적": 5.0, "공격적": 6.5},
        },
        {
            "key": "i_bond",
            "name": "KODEX 단기채권PLUS",
            "weight": 0.30,
            "annual_amount": 900_000,
            "returns": {"보수적": 2.5, "중립적": 3.2, "공격적": 4.0},
        },
    ],
    "ISA": [
        {
            "key": "isa_dividend",
            "name": "TIGER 미국배당다우존스",
            "weight": 0.50,
            "annual_amount": 1_500_000,
            "returns": {"보수적": 5.5, "중립적": 7.5, "공격적": 9.0},
        },
        {
            "key": "isa_sp500",
            "name": "KODEX 미국S&P500",
            "weight": 0.50,
            "annual_amount": 1_500_000,
            "returns": {"보수적": 6.0, "중립적": 8.0, "공격적": 10.0},
        },
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
    annual_isa_deposit: int,
    invest_years: int,
    expected_returns: dict,
    tax_credit_rate: float,
    reinvest_tax_credit: bool,
):
    pension_return = sum(
        cfg["weight"] * expected_returns.get(cfg["key"], 5.0)
        for cfg in ETF_CONFIG["연금저축"]
    )
    irp_return = sum(
        cfg["weight"] * expected_returns.get(cfg["key"], 5.0)
        for cfg in ETF_CONFIG["IRP"]
    )
    isa_return = sum(
        cfg["weight"] * expected_returns.get(cfg["key"], 5.0)
        for cfg in ETF_CONFIG["ISA"]
    )

    total_deposit = annual_pension_deposit + annual_irp_deposit + annual_isa_deposit

    if total_deposit > 0:
        overall_return = (
            (annual_pension_deposit * pension_return)
            + (annual_irp_deposit * irp_return)
            + (annual_isa_deposit * isa_return)
        ) / total_deposit
    else:
        overall_return = (pension_return + irp_return + isa_return) / 3.0

    records = []
    current_asset = float(initial_asset)
    total_principal = float(initial_asset)
    total_tax_reinvested = 0.0

    rate_decimal = overall_return / 100.0

    for year in range(1, invest_years + 1):
        # 세액공제는 연금저축(최대 600만) + IRP(합산 최대 900만) 기준 적용 (ISA 제외)
        eligible_tax_deposit = min(annual_pension_deposit, 6_000_000) + min(
            annual_irp_deposit, max(0, 9_000_000 - min(annual_pension_deposit, 6_000_000))
        )
        tax_refund = eligible_tax_deposit * (tax_credit_rate / 100.0)

        year_deposit = total_deposit
        reinvest_amount = tax_refund if reinvest_tax_credit else 0.0

        total_principal += year_deposit
        total_tax_reinvested += reinvest_amount

        invested_base = current_asset + year_deposit + reinvest_amount
        investment_profit = invested_base * rate_decimal
        current_asset = invested_base + investment_profit

        records.append(
            {
                "연차": year,
                "경과년수": f"{year}년차",
                "총 누적자산": int(current_asset),
                "누적 원금": int(total_principal),
                "누적 투자수익": int(current_asset - total_principal - total_tax_reinvested),
                "누적 세액환급 재투자": int(total_tax_reinvested),
            }
        )

    df_result = pd.DataFrame(records)
    return df_result, overall_return


# =========================================================
# 3. Streamlit UI 메인 화면
# =========================================================

def show_asset_simulation(user_id=None, cookies=None):
    st.set_page_config(page_title="연금 및 ISA 자산 시뮬레이터", layout="wide")
    st.title("📈 통합 자산 성장 시뮬레이터 (연금저축 + IRP + ISA)")
    st.caption("보수적 / 중립적 / 공격적 기대수익률별 자산 성장 추이를 한눈에 비교합니다.")

    st.divider()

    # --- 사이드바: 기본 설정 ---
    st.sidebar.header("⚙️ 기본 입력 설정")

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
    annual_isa = st.sidebar.number_input(
        "ISA 연 납입액", min_value=0, max_value=20_000_000, value=3_000_000, step=500_000
    )

    invest_years = st.sidebar.slider("투자 기간 (년)", min_value=1, max_value=30, value=5, step=1)

    st.sidebar.subheader("🎁 세액공제 설정 (연금/IRP)")
    tax_rate_option = st.sidebar.radio(
        "총급여 기준 세액공제율",
        options=[16.5, 13.2],
        format_func=lambda x: f"{x}% ({'5,500만 이하' if x == 16.5 else '5,500만 초과'})",
    )
    reinvest_tax = st.sidebar.checkbox("세액공제 환급금 매년 재투자하기", value=True)

    # --- 메인 1: 시나리오별 기대수익률 설정 (Tabs) ---
    st.subheader("🎯 시나리오별 종목 기대수익률 설정")
    scenarios = ["보수적", "중립적", "공격적"]
    scenario_tabs = st.tabs([f"🛡️ 보수적", f"⚖️ 중립적", f"🚀 공격적"])

    scenario_returns = {}

    for idx, sc_name in enumerate(scenarios):
        with scenario_tabs[idx]:
            col_p, col_i, col_isa = st.columns(3)
            returns_dict = {}

            with col_p:
                st.markdown("##### 🟢 연금저축 계좌")
                for cfg in ETF_CONFIG["연금저축"]:
                    returns_dict[cfg["key"]] = st.number_input(
                        f"{cfg['name']} (%)",
                        min_value=-10.0,
                        max_value=30.0,
                        value=cfg["returns"][sc_name],
                        step=0.5,
                        key=f"{sc_name}_{cfg['key']}",
                    )

            with col_i:
                st.markdown("##### 🔵 IRP 계좌")
                for cfg in ETF_CONFIG["IRP"]:
                    returns_dict[cfg["key"]] = st.number_input(
                        f"{cfg['name']} (%)",
                        min_value=-10.0,
                        max_value=30.0,
                        value=cfg["returns"][sc_name],
                        step=0.5,
                        key=f"{sc_name}_{cfg['key']}",
                    )

            with col_isa:
                st.markdown("##### 🟠 ISA 계좌")
                for cfg in ETF_CONFIG["ISA"]:
                    returns_dict[cfg["key"]] = st.number_input(
                        f"{cfg['name']} (%)",
                        min_value=-10.0,
                        max_value=30.0,
                        value=cfg["returns"][sc_name],
                        step=0.5,
                        key=f"{sc_name}_{cfg['key']}",
                    )

            scenario_returns[sc_name] = returns_dict

    # --- 계산 실행 ---
    sim_results = {}
    overall_returns = {}

    for sc_name in scenarios:
        df_res, ret = calculate_simulation(
            initial_asset=initial_asset,
            annual_pension_deposit=annual_pension,
            annual_irp_deposit=annual_irp,
            annual_isa_deposit=annual_isa,
            invest_years=invest_years,
            expected_returns=scenario_returns[sc_name],
            tax_credit_rate=tax_rate_option,
            reinvest_tax_credit=reinvest_tax,
        )
        sim_results[sc_name] = df_res
        overall_returns[sc_name] = ret

    st.divider()

    # --- 메인 2: 시나리오 비교 요약 카드 ---
    st.subheader(f"📊 {invest_years}년 후 시나리오별 예상 성과 비교")

    c1, c2, c3 = st.columns(3)
    card_cols = [c1, c2, c3]
    card_icons = ["🛡️", "⚖️", "🚀"]

    for idx, sc_name in enumerate(scenarios):
        df_sc = sim_results[sc_name]
        final_row = df_sc.iloc[-1]
        final_asset = final_row["총 누적자산"]
        final_profit = final_row["누적 투자수익"]
        ret = overall_returns[sc_name]

        with card_cols[idx]:
            st.markdown(f"### {card_icons[idx]} {sc_name} 플랜")
            st.metric("가중평균 수익률", f"연 {ret:.2f}%")
            st.metric("최종 예상 자산", money_sim(final_asset))
            st.metric("순 투자 수익", money_sim(final_profit))

    st.divider()

    # --- 메인 3: 통합 자산 성장 추이 비교 차트 ---
    st.subheader("📈 연도별 자산 성장 추이 비교")

    chart_df = pd.DataFrame({"경과년수": sim_results["중립적"]["경과년수"]})
    for sc_name in scenarios:
        chart_df[f"{sc_name} 자산"] = sim_results[sc_name]["총 누적자산"]
    chart_df["투입 원금"] = sim_results["중립적"]["누적 원금"]

    chart_df = chart_df.set_index("경과년수")
    st.line_chart(chart_df)

    st.divider()

    # --- 메인 4: 연도별 상세 비교 데이터표 ---
    with st.expander("📋 연도별 상세 자산 비교 데이터 보기", expanded=False):
        table_df = pd.DataFrame({"경과년수": sim_results["중립적"]["경과년수"]})
        table_df["누적 원금"] = sim_results["중립적"]["누적 원금"].apply(money_sim)

        for sc_name in scenarios:
            table_df[f"{sc_name} (자산)"] = sim_results[sc_name]["총 누적자산"].apply(
                money_sim
            )
            table_df[f"{sc_name} (수익)"] = sim_results[sc_name]["누적 투자수익"].apply(
                money_sim
            )

        st.dataframe(table_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    show_asset_simulation()