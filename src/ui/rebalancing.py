from datetime import date
import pandas as pd
import streamlit as st

from src.db.contribution_dao import get_user_plan

YEARS = [2026, 2027, 2028, 2029, 2030]
CURRENT_YEAR = date.today().year
CURRENT_MONTH = date.today().month

# 종목별 연간 목표금액 정보 (ISA 계좌 연간 납입액 3,000,000원 반영)
REBALANCING_CONFIG = {
    "연금저축": [
        {"key": "p_sp500", "name": "TIGER 미국S&P500", "target_weight": 0.25, "annual_target": 1_500_000},
        {"key": "p_nasdaq", "name": "KODEX 미국나스닥100", "target_weight": 0.25, "annual_target": 1_500_000},
        {"key": "p_dividend", "name": "KODEX 미국배당다우존스", "target_weight": 0.50, "annual_target": 3_000_000},
    ],
    "IRP": [
        {"key": "i_high_div", "name": "KODEX 주주환원고배당주", "target_weight": 0.30, "annual_target": 900_000},
        {"key": "i_cover_call", "name": "KODEX 200타겟위클리커버드콜", "target_weight": 0.40, "annual_target": 1_200_000},
        {"key": "i_bond", "name": "KODEX 단기채권PLUS", "target_weight": 0.30, "annual_target": 900_000},
    ],
    "ISA": [
        {"key": "isa_dividend", "name": "TIGER 미국배당다우존스", "target_weight": 0.50, "annual_target": 1_500_000},
        {"key": "isa_sp500", "name": "KODEX 미국S&P500", "target_weight": 0.50, "annual_target": 1_500_000},
    ],
}


def money_format(val: float) -> str:
    return f"{int(val):,}원"


def load_data_from_contribution_plan(user_id: str) -> dict:
    """DB에서 이번 달까지의 전체 누적 납입금을 자동으로 로드합니다."""
    rebal_data = {}
    for account in REBALANCING_CONFIG.values():
        for cfg in account:
            rebal_data[cfg["key"]] = 0

    if not user_id:
        return rebal_data

    saved_plan = get_user_plan(user_id)
    if not saved_plan:
        return rebal_data

    # 이번 달(CURRENT_MONTH)까지 포함한 전체 누적 금액 산출
    for year in YEARS:
        if year > CURRENT_YEAR:
            break

        year_str = str(year)
        if year_str not in saved_plan or not isinstance(saved_plan[year_str], dict):
            continue

        monthly_data = saved_plan[year_str].get("monthly_data", {})
        for account in REBALANCING_CONFIG.values():
            for cfg in account:
                key = cfg["key"]
                if key in monthly_data:
                    m_list = monthly_data[key]
                    max_month = CURRENT_MONTH if year == CURRENT_YEAR else 12
                    paid_sum = sum(m_list[:max_month])
                    rebal_data[key] = rebal_data.get(key, 0) + paid_sum

    return rebal_data


def init_rebalancing_state(user_id: str):
    loaded_user_id = st.session_state.get("rebal_loaded_user_id")
    if "rebalancing_data" not in st.session_state or loaded_user_id != user_id:
        st.session_state["rebalancing_data"] = load_data_from_contribution_plan(user_id)
        st.session_state["rebal_loaded_user_id"] = user_id


def render_account_portfolio(account_name: str, config_list: list):
    st.subheader(f"📌 {account_name} 자산 보유 현황")

    current_values = {}
    st.markdown("**종목별 현재 평가 금액 (납입 완료 금액 자동 입력)**")

    num_items = len(config_list)
    cols = st.columns(num_items)

    for idx, cfg in enumerate(config_list):
        item_key = cfg["key"]
        annual_target = cfg.get("annual_target", 0)

        def update_val(k=item_key):
            st.session_state["rebalancing_data"][k] = st.session_state[f"input_{k}"]

        with cols[idx]:
            val = st.number_input(
                f"{cfg['name']}\n(목표 {int(cfg['target_weight'] * 100)}%)",
                min_value=0,
                value=int(st.session_state["rebalancing_data"].get(item_key, 0)),
                step=50_000,
                key=f"input_{item_key}",
                on_change=update_val,
                help="이번 달 납입 후 실제 보유 금액입니다. 평가손익 반영 시 수정하세요.",
            )
            current_values[item_key] = val

            # 종목 연 목표 완납 상태 안내
            if annual_target > 0 and val >= annual_target:
                st.caption("🎉 **올해 목표 완납 완료!**")

    total_current = sum(current_values.values())

    st.divider()

    # 요약 지표
    st.metric("현재 계좌 평가 총액", money_format(total_current))

    # 포트폴리오 비중 비교표
    rows = []
    for cfg in config_list:
        key = cfg["key"]
        name = cfg["name"]
        target_w = cfg["target_weight"]
        annual_target = cfg.get("annual_target", 0)
        c_val = current_values.get(key, 0)
        c_w = (c_val / total_current * 100) if total_current > 0 else 0.0
        diff = c_w - (target_w * 100)

        # 완납 및 상태 표시 구분
        if annual_target > 0 and c_val >= annual_target:
            status = "🎉 올해 목표 완납"
        else:
            status = "🟢 납입 진행 중"

        rows.append({
            "ETF 종목명": name,
            "현재 평가액": money_format(c_val),
            "목표 비중": f"{int(target_w * 100)}%",
            "현재 비중": f"{c_w:.1f}%",
            "비중 차이": f"{diff:+.1f}%p",
            "상태": status,
        })

    display_df = pd.DataFrame(rows)
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def show_rebalancing_dashboard(user_id=None, cookies=None):
    init_rebalancing_state(user_id)
    st.title("📊 계좌 포트폴리오 비중 점검")
    st.caption("이번 달 납입 완료 후 형성된 종목별 비중 현황을 확인합니다.")
    st.divider()

    tab_pension, tab_irp, tab_isa = st.tabs(["🟢 연금저축 계좌", "🔵 IRP 계좌", "🟠 ISA 계좌"])

    with tab_pension:
        render_account_portfolio("연금저축", REBALANCING_CONFIG["연금저축"])

    with tab_irp:
        render_account_portfolio("IRP", REBALANCING_CONFIG["IRP"])

    with tab_isa:
        render_account_portfolio("ISA", REBALANCING_CONFIG["ISA"])


if __name__ == "__main__":
    show_rebalancing_dashboard()