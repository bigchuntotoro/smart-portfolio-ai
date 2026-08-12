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


# =========================================================
# 통합 연금 납입 계획 Dashboard
# =========================================================
def show_pension_dashboard(user_id=None, cookies=None):
    st.title("💰 통합 연금 납입 계획")
    st.caption("연금저축 + IRP 연간 9,000,000원 납입 목표 및 남은 기간 실행 계획")

    # =====================================================
    # 0. DB 조회 및 session_state 동기화 (재로그인/세션유실 대응)
    # =====================================================
    current_loaded_user = st.session_state.get("loaded_user_id")

    # 로그인 사용자가 변경되었거나, 로그아웃 후 위젯 키가 삭제된 경우 DB 재로드
    if user_id and (current_loaded_user != user_id or "p_sp500" not in st.session_state):
        saved_plan = get_user_plan(user_id)
        defaults = {
            "start_month": 9,
            "end_month": 12,
            "p_sp500": 300_000,
            "p_nasdaq": 300_000,
            "p_dividend": 600_000,
            "i_high_div": 180_000,
            "i_cover_call": 240_000,
            "i_bond": 900_000,
        }
        if saved_plan:
            defaults.update(saved_plan)

        for k, v in defaults.items():
            st.session_state[k] = v

        st.session_state["loaded_user_id"] = user_id

    # 기본 세션 키 보장
    for k, v in [
        ("start_month", 9), ("end_month", 12),
        ("p_sp500", 300_000), ("p_nasdaq", 300_000), ("p_dividend", 600_000),
        ("i_high_div", 180_000), ("i_cover_call", 240_000), ("i_bond", 900_000)
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

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
        st.metric(
            "남은 납입 개월",
            f"{remaining_months}개월" if remaining_months > 0 else "잘못된 기간",
        )

    if start_month > end_month:
        st.error("❌ 시작월은 종료월보다 작거나 같아야 합니다.")
        return

    st.divider()

    # =====================================================
    # 2. 현재 납입액 입력 (연금저축 & IRP)
    # =====================================================
    st.subheader("💵 계좌별 현재 납입액 입력")

    # ----- 연금저축 -----
    st.markdown("#### 🟢 연금저축 (연 목표: 6,000,000원)")
    c1, c2, c3 = st.columns(3)

    with c1:
        pension_sp500 = st.number_input(
            "TIGER 미국S&P500",
            min_value=0,
            step=10_000,
            format="%d",
            key="p_sp500",
        )
    with c2:
        pension_nasdaq = st.number_input(
            "KODEX 미국나스닥100",
            min_value=0,
            step=10_000,
            format="%d",
            key="p_nasdaq",
        )
    with c3:
        pension_dividend = st.number_input(
            "KODEX 미국배당다우존스",
            min_value=0,
            step=10_000,
            format="%d",
            key="p_dividend",
        )

    # 연금저축 합계 표시
    pension_current = pension_sp500 + pension_nasdaq + pension_dividend
    pension_rate = (pension_current / 6_000_000 * 100) if 6_000_000 > 0 else 0.0
    st.info(f"🟢 **연금저축 현재 납입 합계:** {money(pension_current)} / 6,000,000원 (달성률: {min(pension_rate, 100.0):.1f}%)")

    st.write("")

    # ----- IRP -----
    st.markdown("#### 🔵 IRP (연 목표: 3,000,000원)")
    i1, i2, i3 = st.columns(3)

    with i1:
        irp_high_div = st.number_input(
            "KODEX 주주환원고배당주",
            min_value=0,
            step=10_000,
            format="%d",
            key="i_high_div",
        )
    with i2:
        irp_cover_call = st.number_input(
            "KODEX 200타겟위클리커버드콜",
            min_value=0,
            step=10_000,
            format="%d",
            key="i_cover_call",
        )
    with i3:
        irp_bond = st.number_input(
            "KODEX 단기채권PLUS",
            min_value=0,
            step=10_000,
            format="%d",
            key="i_bond",
        )

    # IRP 합계 표시
    irp_current = irp_high_div + irp_cover_call + irp_bond
    irp_rate = (irp_current / 3_000_000 * 100) if 3_000_000 > 0 else 0.0
    st.info(f"🔵 **IRP 현재 납입 합계:** {money(irp_current)} / 3,000,000원 (달성률: {min(irp_rate, 100.0):.1f}%)")

    # 전체 총 납입 합계 요약
    total_current = pension_current + irp_current
    total_rate = (total_current / 9_000_000 * 100) if 9_000_000 > 0 else 0.0
    st.caption(f"💡 **총 계좌 합계:** {money(total_current)} / 9,000,000원 (전체 달성률: {min(total_rate, 100.0):.1f}%)")

    # -----------------------------------------------------
    # 💾 DB 저장 버튼
    # -----------------------------------------------------
    st.write("")
    btn_col1, btn_col2 = st.columns([1, 2])
    with btn_col1:
        if st.button("💾 DB에 납입 계획 저장하기", use_container_width=True, type="primary"):
            if not user_id:
                st.error("❌ 로그인 정보가 없어 저장할 수 없습니다.")
            else:
                current_plan_data = {
                    "p_sp500": pension_sp500,
                    "p_nasdaq": pension_nasdaq,
                    "p_dividend": pension_dividend,
                    "i_high_div": irp_high_div,
                    "i_cover_call": irp_cover_call,
                    "i_bond": irp_bond,
                    "start_month": start_month,
                    "end_month": end_month,
                }
                success = save_user_plan(user_id, current_plan_data)
                if success:
                    st.toast("✅ DB에 납입 계획이 성공적으로 저장되었습니다!", icon="💾")
                    st.session_state["loaded_user_id"] = user_id
                    st.rerun()
                else:
                    st.error("❌ DB 저장 중 오류가 발생했습니다.")

    st.divider()

    # =====================================================
    # 3. 데이터 구조체 생성 및 계산
    # =====================================================
    all_items = [
        # 연금저축
        ContributionItem(
            account="연금저축",
            name="TIGER 미국S&P500",
            annual_target=1_500_000,
            weight=0.25,
            current_amount=pension_sp500,
        ),
        ContributionItem(
            account="연금저축",
            name="KODEX 미국나스닥100",
            annual_target=1_500_000,
            weight=0.25,
            current_amount=pension_nasdaq,
        ),
        ContributionItem(
            account="연금저축",
            name="KODEX 미국배당다우존스",
            annual_target=3_000_000,
            weight=0.50,
            current_amount=pension_dividend,
        ),
        # IRP
        ContributionItem(
            account="IRP",
            name="KODEX 주주환원고배당주",
            annual_target=900_000,
            weight=0.30,
            current_amount=irp_high_div,
        ),
        ContributionItem(
            account="IRP",
            name="KODEX 200타겟위클리커버드콜",
            annual_target=1_200_000,
            weight=0.40,
            current_amount=irp_cover_call,
        ),
        ContributionItem(
            account="IRP",
            name="KODEX 단기채권PLUS",
            annual_target=900_000,
            weight=0.30,
            current_amount=irp_bond,
        ),
    ]

    # 납입 계산 수행
    all_items = calculate_contribution_plan(all_items)
    plan = calculate_remaining_plan(all_items, start_month, end_month)
    summary = get_summary(all_items)

    # =====================================================
    # 4. 올해 납입 현황 및 진행률 (KPI)
    # =====================================================
    st.subheader("🎯 올해 전체 납입 현황")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("올해 총 목표", money(summary["total_target"]))
    with k2:
        st.metric("현재 총 납입액", money(summary["total_current"]))
    with k3:
        st.metric("남은 목표 금액", money(summary["total_remaining"]))
    with k4:
        st.metric("남은 개월 수", f"{remaining_months}개월")

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

        st.markdown(f"### {'🟢' if account == '연금저축' else '🔵'} {account}")

        acc_target = sum(item["target_amount"] for item in account_items)
        acc_current = sum(item["current_amount"] for item in account_items)
        acc_remaining = sum(item["remaining_amount"] for item in account_items)
        acc_monthly = (
            round(acc_remaining / remaining_months)
            if remaining_months > 0
            else 0
        )

        ac1, ac2, ac3, ac4 = st.columns(4)
        with ac1:
            st.metric("연간 목표", money(acc_target))
        with ac2:
            st.metric("현재 납입", money(acc_current))
        with ac3:
            st.metric("남은 금액", money(acc_remaining))
        with ac4:
            st.metric("월 평균 납입", money(acc_monthly))

        # ETF 상세 항목
        for item in account_items:
            e1, e2, e3, e4 = st.columns(4)
            with e1:
                st.write(f"**{item['name']}**")
            with e2:
                st.write(f"목표: {money(item['target_amount'])}")
            with e3:
                st.write(f"현재: {money(item['current_amount'])}")
            with e4:
                if item["remaining_amount"] <= 0:
                    st.success("🎉 완납 (월 0원)")
                else:
                    st.info(f"월 {money(item['monthly_amount'])}")
        st.write("")

    st.divider()

    # =====================================================
    # 6. 월별 납입 상세 스케줄
    # =====================================================
    st.subheader("📅 월별 상세 납입 스케줄")

    schedule = build_monthly_schedule(plan, start_month, end_month)

    for month_data in schedule:
        m_num = month_data["month"]
        with st.expander(f"📅 {m_num}월 납입 계획 — 총 {money(month_data['total'])}"):
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