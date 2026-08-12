import pandas as pd
import plotly.express as px
import streamlit as st

from src.core.contribution_plan import (
    ContributionItem,
    build_monthly_schedule,
    calculate_contribution_plan,
    calculate_remaining_plan,
    get_summary,
)
from src.db.contribution_dao import get_user_plan, save_user_plan


# =========================================================
# 금액 표시 헬퍼 함수
# =========================================================
def money(value):
    return f"{int(value):,}원"


# ETF 메타 데이터 정의
ETF_CONFIG = {
    "연금저축": [
        {"key": "p_sp500", "name": "TIGER 미국S&P500", "target": 1_500_000, "weight": 0.25},
        {"key": "p_nasdaq", "name": "KODEX 미국나스닥100", "target": 1_500_000, "weight": 0.25},
        {"key": "p_dividend", "name": "KODEX 미국배당다우존스", "target": 3_000_000, "weight": 0.50},
    ],
    "IRP": [
        {"key": "i_high_div", "name": "KODEX 주주환원고배당주", "target": 900_000, "weight": 0.30},
        {"key": "i_cover_call", "name": "KODEX 200타겟위클리커버드콜", "target": 1_200_000, "weight": 0.40},
        {"key": "i_bond", "name": "KODEX 단기채권PLUS", "target": 900_000, "weight": 0.30},
    ],
}


# DataFrame 생성 헬퍼 함수 (남은 납입 기간 기준 월 기준금액 계산)
def create_account_df(account_name, remaining_months):
    month_cols = [f"{m}월" for m in range(1, 13)]
    rows = []
    safe_months = max(remaining_months, 1)

    for cfg in ETF_CONFIG[account_name]:
        key = cfg["key"]
        monthly_list = st.session_state.get("monthly_data", {}).get(key, [0] * 12)
        
        # 길이가 12가 아닌 예외 케이스 방지
        if len(monthly_list) < 12:
            monthly_list = monthly_list + [0] * (12 - len(monthly_list))

        current_sum = sum(monthly_list)
        remaining_amount = max(cfg["target"] - current_sum, 0)

        row = {
            "ETF종목명": cfg["name"],
            "목표 비중": f"{int(cfg['weight'] * 100)}%",
            "연 목표금액": cfg["target"],
            "월 기준금액(남은 기간)": remaining_amount // safe_months,
        }
        for idx, m_col in enumerate(month_cols):
            row[m_col] = monthly_list[idx]
        rows.append(row)

    return pd.DataFrame(rows)


# =========================================================
# 통합 연금 납입 계획 Dashboard
# =========================================================
def show_pension_dashboard(user_id=None, cookies=None):
    st.title("💰 통합 연금 납입 계획")
    st.caption("연금저축(600만원/66.7%) + IRP(300만원/33.3%) 연간 9,000,000원 목표 실행 계획")

    # =====================================================
    # 0. DB 조회 및 session_state 동기화
    # =====================================================
    current_loaded_user = st.session_state.get("loaded_user_id")

    default_monthly = {
        cfg["key"]: [0] * 12
        for account in ETF_CONFIG.values()
        for cfg in account
    }

    # 사용자가 변경되었거나 처음 로드될 때
    if user_id and (current_loaded_user != user_id or "monthly_data" not in st.session_state):
        saved_plan = get_user_plan(user_id)

        if saved_plan:
            st.session_state["start_month"] = saved_plan.get("start_month", 9)
            st.session_state["end_month"] = saved_plan.get("end_month", 12)
            st.session_state["monthly_data"] = saved_plan.get("monthly_data", default_monthly)
        else:
            st.session_state["start_month"] = 9
            st.session_state["end_month"] = 12
            st.session_state["monthly_data"] = default_monthly

        st.session_state["loaded_user_id"] = user_id
        
        # data_editor 위젯 세션 캐시 제거 (유저 전환 시 이전 입력을 초기화)
        st.session_state.pop("editor_pension", None)
        st.session_state.pop("editor_irp", None)

    # 기본 세션 키 보장
    if "monthly_data" not in st.session_state:
        st.session_state["monthly_data"] = default_monthly

    # =====================================================
    # 1. 납입 기간 설정
    # =====================================================
    st.subheader("📅 남은 납입 기간 설정")
    col1, col2, col3 = st.columns(3)

    with col1:
        start_month = st.number_input(
            "시작월",
            min_value=1,
            max_value=12,
            step=1,
            key="start_month",
        )

    with col2:
        end_month = st.number_input(
            "종료월",
            min_value=1,
            max_value=12,
            step=1,
            key="end_month",
        )

    remaining_months = end_month - start_month + 1

    with col3:
        if remaining_months > 0:
            st.metric("남은 납입 개월", f"{remaining_months}개월")
        else:
            st.metric("남은 납입 개월", "오류", delta="기간 확인 필요", delta_color="inverse")

    if start_month > end_month:
        st.error("❌ 시작월은 종료월보다 작거나 같아야 합니다. 납입 기간을 다시 확인해주세요.")
        return

    st.divider()

    # =====================================================
    # 2. 계좌별 월별 납입액 입력 (st.data_editor 매트릭스)
    # =====================================================
    st.subheader("💵 계좌별 월별 현재 납입액 입력")
    st.caption(
        f"💡 **남은 납입 기간({remaining_months}개월)** 기준 필요한 월 기준금액과 비중을 확인하면서 입력하세요."
    )

    month_cols = [f"{m}월" for m in range(1, 13)]
    calculated_totals = {}

    # 공통 Column Config 생성 헬퍼
    def get_column_config():
        cfg = {
            "ETF종목명": st.column_config.TextColumn("ETF종목명", width="medium"),
            "목표 비중": st.column_config.TextColumn("목표 비중", width="small"),
            "연 목표금액": st.column_config.NumberColumn("연 목표금액", format="%,d원", width="small"),
            "월 기준금액(남은 기간)": st.column_config.NumberColumn(
                f"월 기준금액({remaining_months}개월)", format="%,d원", width="small"
            ),
        }
        for m in month_cols:
            cfg[m] = st.column_config.NumberColumn(f"{m}", min_value=0, step=10000, format="%,d원")
        return cfg

    # ----- 🟢 연금저축 매트릭스 입력 -----
    df_pension = create_account_df("연금저축", remaining_months)
    p_target_total = 6_000_000
    p_weight_total = "66.7%"

    st.markdown(f"#### 🟢 연금저축 (연 목표: {money(p_target_total)} | 계좌 비중: {p_weight_total})")

    edited_pension_df = st.data_editor(
        df_pension,
        key="editor_pension",
        hide_index=True,
        disabled=["ETF종목명", "목표 비중", "연 목표금액", "월 기준금액(남은 기간)"],
        column_config=get_column_config(),
        use_container_width=True,
    )

    pension_total = 0
    # iloc[idx] 대신 ETF종목명 매칭 방식으로 안전하게 수정
    for cfg in ETF_CONFIG["연금저축"]:
        matched_row = edited_pension_df[edited_pension_df["ETF종목명"] == cfg["name"]]
        if not matched_row.empty:
            row_vals = [
                int(v) if pd.notna(v) else 0
                for v in matched_row.iloc[0][month_cols].tolist()
            ]
        else:
            row_vals = [0] * 12

        st.session_state["monthly_data"][cfg["key"]] = row_vals
        tot = sum(row_vals)
        calculated_totals[cfg["key"]] = tot
        pension_total += tot

    p_remaining = max(p_target_total - pension_total, 0)
    p_monthly_req = p_remaining // remaining_months if remaining_months > 0 else 0
    p_rate = (pension_total / p_target_total * 100) if p_target_total > 0 else 0.0

    st.info(
        f"🟢 **연금저축 현황:** 누적 납입 {money(pension_total)} / {money(p_target_total)} "
        f"(달성률: **{min(p_rate, 100.0):.1f}%**) | **남은 {remaining_months}개월간 필요 월 납입액:** **{money(p_monthly_req)}**"
    )

    st.write("")

    # ----- 🔵 IRP 매트릭스 입력 -----
    df_irp = create_account_df("IRP", remaining_months)
    i_target_total = 3_000_000
    i_weight_total = "33.3%"

    st.markdown(f"#### 🔵 IRP (연 목표: {money(i_target_total)} | 계좌 비중: {i_weight_total})")

    edited_irp_df = st.data_editor(
        df_irp,
        key="editor_irp",
        hide_index=True,
        disabled=["ETF종목명", "목표 비중", "연 목표금액", "월 기준금액(남은 기간)"],
        column_config=get_column_config(),
        use_container_width=True,
    )

    irp_total = 0
    # iloc[idx] 대신 ETF종목명 매칭 방식으로 안전하게 수정
    for cfg in ETF_CONFIG["IRP"]:
        matched_row = edited_irp_df[edited_irp_df["ETF종목명"] == cfg["name"]]
        if not matched_row.empty:
            row_vals = [
                int(v) if pd.notna(v) else 0
                for v in matched_row.iloc[0][month_cols].tolist()
            ]
        else:
            row_vals = [0] * 12

        st.session_state["monthly_data"][cfg["key"]] = row_vals
        tot = sum(row_vals)
        calculated_totals[cfg["key"]] = tot
        irp_total += tot

    i_remaining = max(i_target_total - irp_total, 0)
    i_monthly_req = i_remaining // remaining_months if remaining_months > 0 else 0
    i_rate = (irp_total / i_target_total * 100) if i_target_total > 0 else 0.0

    st.info(
        f"🔵 **IRP 현황:** 누적 납입 {money(irp_total)} / {money(i_target_total)} "
        f"(달성률: **{min(i_rate, 100.0):.1f}%**) | **남은 {remaining_months}개월간 필요 월 납입액:** **{money(i_monthly_req)}**"
    )

    grand_target = p_target_total + i_target_total
    grand_total = pension_total + irp_total
    grand_remaining = max(grand_target - grand_total, 0)
    grand_monthly_req = grand_remaining // remaining_months if remaining_months > 0 else 0
    grand_rate = (grand_total / grand_target * 100) if grand_target > 0 else 0.0

    st.caption(
        f"💡 **통합 전체 누적 합계:** {money(grand_total)} / {money(grand_target)} "
        f"(전체 달성률: **{min(grand_rate, 100.0):.1f}%**) | **통합 남은 {remaining_months}개월 필요 월 납입액:** **{money(grand_monthly_req)}**"
    )

    # -----------------------------------------------------
    # 💾 DB 저장 버튼
    # -----------------------------------------------------
    st.write("")
    btn_col1, _ = st.columns([1, 2])
    with btn_col1:
        if st.button("💾 DB에 납입 계획 저장하기", use_container_width=True, type="primary"):
            if not user_id:
                st.error("❌ 로그인 정보가 없어 저장할 수 없습니다.")
            else:
                current_plan_data = {
                    "start_month": start_month,
                    "end_month": end_month,
                    "monthly_data": st.session_state["monthly_data"],
                }

                success = save_user_plan(user_id, current_plan_data)
                if success:
                    st.toast("✅ DB에 월별 납입 내역이 성공적으로 저장되었습니다!", icon="💾")
                    st.session_state["loaded_user_id"] = user_id
                else:
                    st.error("❌ DB 저장 중 오류가 발생했습니다.")

    st.divider()

    # =====================================================
    # 3. 데이터 구조체 생성 및 계산
    # =====================================================
    all_items = []
    for account, cfgs in ETF_CONFIG.items():
        for cfg in cfgs:
            all_items.append(
                ContributionItem(
                    account=account,
                    name=cfg["name"],
                    annual_target=cfg["target"],
                    weight=cfg["weight"],
                    current_amount=calculated_totals.get(cfg["key"], 0),
                )
            )

    all_items = calculate_contribution_plan(all_items)
    plan = calculate_remaining_plan(all_items, start_month, end_month)
    summary = get_summary(all_items)

    # =====================================================
    # 4. 올해 납입 현황 및 진행률 (KPI)
    # =====================================================
    st.subheader(f"🎯 남은 {remaining_months}개월 납입 현황 및 필요 기준액")

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("올해 총 목표", money(summary["total_target"]))
    with k2:
        st.metric("현재 총 납입액", money(summary["total_current"]))
    with k3:
        st.metric("남은 목표 금액", money(summary["total_remaining"]))
    with k4:
        st.metric("남은 기간", f"{remaining_months}개월")
    with k5:
        st.metric("월 필요 납입액", money(grand_monthly_req))

    if summary["total_target"] > 0:
        progress = min(
            max(summary["total_current"] / summary["total_target"], 0.0), 1.0
        )
        st.progress(progress)
        st.caption(f"전체 달성률: {progress * 100:.1f}%")

    st.divider()

    # =====================================================
    # 5. ETF별 남은 납입 실행 계획
    # =====================================================
    st.subheader(f"📈 {start_month}~{end_month}월 계좌/ETF별 남은 납입 계획")

    for account in ["연금저축", "IRP"]:
        account_items = [item for item in plan if item["account"] == account]
        acc_target = sum(item["target_amount"] for item in account_items)
        acc_weight = "66.7%" if account == "연금저축" else "33.3%"
        acc_current = sum(item["current_amount"] for item in account_items)
        acc_remaining = sum(item["remaining_amount"] for item in account_items)
        acc_monthly_req = (
            acc_remaining // remaining_months if remaining_months > 0 else 0
        )

        icon = "🟢" if account == "연금저축" else "🔵"
        st.markdown(f"### {icon} {account}")
        st.caption(f"계좌 비중: {acc_weight} | 남은 기간 월 필요: {money(acc_monthly_req)}")

        ac1, ac2, ac3, ac4 = st.columns(4)
        with ac1:
            st.metric("연간 목표", money(acc_target))
        with ac2:
            st.metric("현재 납입", money(acc_current))
        with ac3:
            st.metric("남은 금액", money(acc_remaining))
        with ac4:
            st.metric(f"월 필요액 ({remaining_months}개월)", money(acc_monthly_req))

        for item in account_items:
            cfg_match = next(
                (c for c in ETF_CONFIG[account] if c["name"] == item["name"]), None
            )
            weight_str = f"{int(cfg_match['weight'] * 100)}%" if cfg_match else "-"
            item_rem = item["remaining_amount"]
            item_monthly_base = (
                item_rem // remaining_months if remaining_months > 0 else 0
            )

            e1, e2, e3, e4 = st.columns([1.5, 1.1, 1, 1.2])
            with e1:
                st.markdown(f"**{item['name']}** `비중 {weight_str}`")
            with e2:
                st.write(f"월 필요액: **{money(item_monthly_base)}**")
            with e3:
                st.write(f"현재: {money(item['current_amount'])}")
            with e4:
                if item["remaining_amount"] <= 0:
                    st.success("🎉 완납 (월 0원)")
                else:
                    st.info(f"실행 월: {money(item['monthly_amount'])}")
        st.write("")

    st.divider()

    # =====================================================
    # 6. 월별 납입 상세 스케줄
    # =====================================================
    st.subheader("📅 월별 상세 납입 스케줄")

    schedule = build_monthly_schedule(plan, start_month, end_month)

    for month_data in schedule:
        m_num = month_data["month"]
        rate_vs_req = (
            (month_data["total"] / grand_monthly_req * 100)
            if grand_monthly_req > 0
            else 100
        )
        with st.expander(
            f"📅 {m_num}월 납입 계획 — 총 {money(month_data['total'])} (필요 월액 대비 {rate_vs_req:.0f}%)"
        ):
            for item in month_data["items"]:
                if item["amount"] > 0:
                    st.write(f"• **{item['name']}**: {money(item['amount'])}")

    # =====================================================
    # 7. 완납 종목 안내
    # =====================================================
    completed_items = [
        item for item in all_items if item.current_amount >= item.annual_target
    ]
    if completed_items:
        st.divider()
        for comp in completed_items:
            st.success(
                f"✅ **{comp.name}** ({comp.account})은 올해 목표 "
                f"{money(comp.annual_target)}를 이미 달성(완납)했습니다."
            )