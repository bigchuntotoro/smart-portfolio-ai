from datetime import date
import pandas as pd
import streamlit as st

# 1. 납입 계획 데이터 DAO 및 기본 설정 불러오기
from src.db.contribution_dao import get_user_plan

YEARS = [2026, 2027, 2028, 2029, 2030]
CURRENT_YEAR = date.today().year
CURRENT_MONTH = date.today().month

REBALANCING_CONFIG = {
    "연금저축": [
        {"key": "p_sp500", "name": "TIGER 미국S&P500", "target_weight": 0.25, "default_monthly": 125_000},
        {"key": "p_nasdaq", "name": "KODEX 미국나스닥100", "target_weight": 0.25, "default_monthly": 125_000},
        {"key": "p_dividend", "name": "KODEX 미국배당다우존스", "target_weight": 0.50, "default_monthly": 250_000},
    ],
    "IRP": [
        {"key": "i_high_div", "name": "KODEX 주주환원고배당주", "target_weight": 0.30, "default_monthly": 75_000},
        {"key": "i_cover_call", "name": "KODEX 200타겟위클리커버드콜", "target_weight": 0.40, "default_monthly": 100_000},
        {"key": "i_bond", "name": "KODEX 단기채권PLUS", "target_weight": 0.30, "default_monthly": 75_000},
    ],
}


def money_format(val: float) -> str:
    """원 단위 통화 포맷팅"""
    return f"{int(val):,}원"


# =========================================================
# 2. 납입 계획 DB 데이터 로드 및 리밸런싱 데이터 변환
# =========================================================

def load_data_from_contribution_plan(user_id: str) -> dict:
    """통합 납입 계획 DB 데이터를 읽어와 리밸런싱용 데이터(현재 평가액 & 이달 적립금)로 변환"""
    rebal_data = {}

    # 기본값 설정
    for account in REBALANCING_CONFIG.values():
        for cfg in account:
            rebal_data[cfg["key"]] = 0
    rebal_data["dep_연금저축"] = 500_000
    rebal_data["dep_IRP"] = 250_000

    if not user_id:
        return rebal_data

    saved_plan = get_user_plan(user_id)
    if not saved_plan:
        return rebal_data

    # 1. 과거~현재까지의 실제 월별 납입 누적액 계산 (현재 평가액으로 사용)
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
                    # 현재 연도면 현재 월까지, 과거 연도면 12월 전체 누적
                    max_month = CURRENT_MONTH if year == CURRENT_YEAR else 12
                    paid_sum = sum(m_list[:max_month])
                    rebal_data[key] = rebal_data.get(key, 0) + paid_sum

    # 2. 이번 달 적립 예정금 연동 (현재 연도 현재 월 납입 계획액 또는 자동 분배액)
    curr_year_str = str(CURRENT_YEAR)
    if curr_year_str in saved_plan:
        monthly_data = saved_plan[curr_year_str].get("monthly_data", {})

        # 이번 달 실제 입력되어 있는 금액이 있으면 그것을 우선 사용
        pension_this_month = sum(
            monthly_data.get(cfg["key"], [0] * 12)[CURRENT_MONTH - 1]
            for cfg in REBALANCING_CONFIG["연금저축"]
            if len(monthly_data.get(cfg["key"], [])) >= CURRENT_MONTH
        )
        irp_this_month = sum(
            monthly_data.get(cfg["key"], [0] * 12)[CURRENT_MONTH - 1]
            for cfg in REBALANCING_CONFIG["IRP"]
            if len(monthly_data.get(cfg["key"], [])) >= CURRENT_MONTH
        )

        if pension_this_month > 0:
            rebal_data["dep_연금저축"] = pension_this_month
        if irp_this_month > 0:
            rebal_data["dep_IRP"] = irp_this_month

    return rebal_data


def init_rebalancing_state(user_id: str):
    """세션 상태 초기화 및 DB 데이터 연동"""
    loaded_user_id = st.session_state.get("rebal_loaded_user_id")

    if "rebalancing_data" not in st.session_state or loaded_user_id != user_id:
        st.session_state["rebalancing_data"] = load_data_from_contribution_plan(user_id)
        st.session_state["rebal_loaded_user_id"] = user_id


# =========================================================
# 3. 매수 배분 연산 엔진
# =========================================================

def calculate_buy_allocation(config_list: list, current_values: dict, monthly_deposit: int):
    total_current = sum(current_values.values())
    total_after_deposit = total_current + monthly_deposit

    rows = []
    for cfg in config_list:
        key = cfg["key"]
        name = cfg["name"]
        target_w = cfg["target_weight"]

        c_val = current_values.get(key, 0)
        c_w = (c_val / total_current * 100) if total_current > 0 else 0.0
        target_val = total_after_deposit * target_w

        rows.append({
            "key": key,
            "종목명": name,
            "목표비중": f"{int(target_w * 100)}%",
            "현재 평가액": c_val,
            "현재 비중": c_w,
            "목표 평가액": int(target_val),
        })

    deposit_alloc = {}
    if monthly_deposit > 0:
        needed_amounts = {r["key"]: max(0, r["목표 평가액"] - r["현재 평가액"]) for r in rows}
        total_needed = sum(needed_amounts.values())

        if total_needed > 0:
            for key, needed in needed_amounts.items():
                alloc = min(needed, monthly_deposit * (needed / total_needed))
                deposit_alloc[key] = int(alloc)
        else:
            for cfg in config_list:
                deposit_alloc[cfg["key"]] = int(monthly_deposit * cfg["target_weight"])
    else:
        for cfg in config_list:
            deposit_alloc[cfg["key"]] = 0

    df = pd.DataFrame(rows)
    df["추천 매수액"] = df["key"].map(deposit_alloc)
    return df, total_current, total_after_deposit


# =========================================================
# 4. Streamlit 대시보드 UI
# =========================================================

def show_rebalancing_dashboard(user_id=None, cookies=None):
    # DB에서 연금 납입 계획 데이터를 자동 로딩
    init_rebalancing_state(user_id)

    st.title("⚖️ 5년 적립식 매수 가이드")
    st.caption("📂 '통합 연금 납입 계획' DB 데이터를 자동으로 불러와 이번 달 매수 추천 금액을 산출합니다.")
    st.divider()

    tab_pension, tab_irp = st.tabs(["🟢 연금저축 계좌 (월 50만 원)", "🔵 IRP 계좌 (월 25만 원)"])

    with tab_pension:
        render_account_rebalancing("연금저축", REBALANCING_CONFIG["연금저축"])

    with tab_irp:
        render_account_rebalancing("IRP", REBALANCING_CONFIG["IRP"])


def render_account_rebalancing(account_name: str, config_list: list):
    st.subheader(f"📌 {account_name} 잔고 및 이달 적립금 (DB 연동 완료)")

    col_input, col_deposit = st.columns([2, 1])

    current_values = {}
    with col_input:
        st.markdown("**1. 현재 종목별 평가 금액 (누적 실제 납입금 자동 로딩)**")
        c1, c2, c3 = st.columns(3)
        cols = [c1, c2, c3]

        for idx, cfg in enumerate(config_list):
            item_key = cfg["key"]

            def update_val(k=item_key):
                st.session_state["rebalancing_data"][k] = st.session_state[f"input_{k}"]

            with cols[idx % 3]:
                val = st.number_input(
                    f"{cfg['name']}\n(목표 {int(cfg['target_weight'] * 100)}%)",
                    min_value=0,
                    value=int(st.session_state["rebalancing_data"].get(item_key, 0)),
                    step=50_000,
                    key=f"input_{item_key}",
                    on_change=update_val,
                    help="DB에 저장된 과거~현재 누적 실제 납입금입니다. 평가 손익이 있다면 수정하세요.",
                )
                current_values[item_key] = val

    with col_deposit:
        st.markdown("**2. 이번 달 신규 납입금**")
        dep_key = f"dep_{account_name}"

        def update_dep(k=dep_key):
            st.session_state["rebalancing_data"][k] = st.session_state[f"input_{k}"]

        monthly_deposit = st.number_input(
            "이달 매수 예정금 (원)",
            min_value=0,
            value=int(st.session_state["rebalancing_data"].get(dep_key, 0)),
            step=50_000,
            key=f"input_{dep_key}",
            on_change=update_dep,
        )

    # 매수 추천 연산
    df_result, total_current, total_after = calculate_buy_allocation(
        config_list, current_values, monthly_deposit
    )

    st.divider()

    # 요약 카드
    m1, m2, m3 = st.columns(3)
    m1.metric("현재 평가 총액", money_format(total_current))
    m2.metric("이번 달 매수 예정금", money_format(monthly_deposit))
    m3.metric("매수 후 예상 총자산", money_format(total_after))

    st.subheader("🛒 이번 달 추천 매수 가이드")

    display_df = pd.DataFrame()
    display_df["ETF 종목명"] = df_result["종목명"]
    display_df["목표 비중"] = df_result["목표비중"]
    display_df["현재 비중"] = df_result["현재 비중"].apply(lambda x: f"{x:.1f}%")
    display_df["현재 평가액"] = df_result["현재 평가액"].apply(money_format)
    display_df["💵 이번 달 매수할 금액"] = df_result["추천 매수액"].apply(
        lambda x: f"🟢 {money_format(x)} 매수" if x > 0 else "➖ (이달 매수 안함)"
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    show_rebalancing_dashboard()