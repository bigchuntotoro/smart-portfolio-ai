from datetime import date
import pandas as pd
import streamlit as st

from src.db.contribution_dao import (
    get_user_plan,
    save_user_plan,
)

# =========================================================
# 기본 설정 및 상수
# =========================================================

YEARS = [2026, 2027, 2028, 2029, 2030]
CURRENT_YEAR = date.today().year
CURRENT_MONTH = date.today().month

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
    "ISA": [
        {"key": "isa_sp500", "name": "TIGER 미국S&P500", "target": 1_500_000, "weight": 0.50},
        {"key": "isa_nasdaq", "name": "KODEX 미국나스닥100TR", "target": 900_000, "weight": 0.30},
        {"key": "isa_semicon", "name": "TIGER 미국반도체FactSet", "target": 600_000, "weight": 0.20},
    ],
}


# =========================================================
# 유틸리티 함수
# =========================================================

def money(value: float) -> str:
    """숫자를 통화 포맷 문자열로 변환합니다."""
    return f"{int(value):,}원"


def ceil_div(value: int, divisor: int) -> int:
    """나눗셈 올림 처리 함수"""
    if divisor <= 0 or value <= 0:
        return 0
    return (value + divisor - 1) // divisor


# =========================================================
# 데이터 초기화 및 변환 함수
# =========================================================

def _default_monthly_data() -> dict:
    return {cfg["key"]: [0] * 12 for account in ETF_CONFIG.values() for cfg in account}


def _default_yearly_data() -> dict:
    yearly_data = {}
    for year in YEARS:
        start_month = 9 if year == 2026 else 1
        yearly_data[year] = {
            "start_month": start_month,
            "end_month": 12,
            "monthly_data": _default_monthly_data(),
        }
    return yearly_data


def _normalize_monthly_list(values) -> list:
    if values is None:
        values = []
    values = list(values)
    if len(values) < 12:
        values += [0] * (12 - len(values))

    result = []
    for value in values[:12]:
        try:
            result.append(0 if pd.isna(value) else max(int(value), 0))
        except (TypeError, ValueError):
            result.append(0)
    return result


def _migrate_saved_plan(saved_plan: dict) -> dict:
    yearly_data = _default_yearly_data()
    if not saved_plan:
        return yearly_data

    # 기존 단일연도 레거시 구조 대응
    if "monthly_data" in saved_plan and "start_month" in saved_plan:
        yearly_data[2026]["start_month"] = saved_plan.get("start_month", 9)
        yearly_data[2026]["end_month"] = saved_plan.get("end_month", 12)
        legacy_data = saved_plan.get("monthly_data", {})
        for key, values in legacy_data.items():
            if key in yearly_data[2026]["monthly_data"]:
                yearly_data[2026]["monthly_data"][key] = _normalize_monthly_list(values)
        return yearly_data

    # 연도별 다중 데이터 구조 처리
    for year in YEARS:
        year_key = str(year)
        if year_key not in saved_plan or not isinstance(saved_plan[year_key], dict):
            continue

        saved_year = saved_plan[year_key]
        yearly_data[year]["start_month"] = saved_year.get("start_month", yearly_data[year]["start_month"])
        yearly_data[year]["end_month"] = saved_year.get("end_month", yearly_data[year]["end_month"])

        saved_monthly = saved_year.get("monthly_data", {})
        if isinstance(saved_monthly, dict):
            for key, values in saved_monthly.items():
                if key in yearly_data[year]["monthly_data"]:
                    yearly_data[year]["monthly_data"][key] = _normalize_monthly_list(values)

    return yearly_data


# =========================================================
# 계산 관련 헬퍼 함수
# =========================================================

def _get_remaining_start_month(year: int, start_month: int) -> int:
    if year == CURRENT_YEAR:
        return max(start_month, CURRENT_MONTH + 1)
    return start_month


def _get_etf_monthly_values(year: int, etf_key: str) -> list:
    yearly_data = st.session_state.get("yearly_data", {})
    monthly_data = yearly_data.get(year, {}).get("monthly_data", {})
    return _normalize_monthly_list(monthly_data.get(etf_key, [0] * 12))


def _get_actual_etf_total(year: int, etf_key: str) -> int:
    return sum(_get_etf_monthly_values(year, etf_key))


def _get_actual_account_total(year: int, account: str) -> int:
    return sum(_get_actual_etf_total(year, cfg["key"]) for cfg in ETF_CONFIG[account])


def _get_actual_total(year: int) -> int:
    return sum(_get_actual_account_total(year, acc) for acc in ETF_CONFIG.keys())


def _get_last_actual_month(year: int, etf_key: str, start_month: int, end_month: int):
    values = _get_etf_monthly_values(year, etf_key)
    last_month = None
    for month in range(start_month, end_month + 1):
        if values[month - 1] > 0:
            last_month = month
    return last_month


def _get_etf_remaining_period(year: int, etf_key: str, start_month: int, end_month: int):
    base_start = _get_remaining_start_month(year, start_month)
    if base_start > end_month:
        return base_start, 0

    last_actual_month = _get_last_actual_month(year, etf_key, start_month, end_month)
    remaining_start = base_start if last_actual_month is None else max(base_start, last_actual_month + 1)

    if remaining_start > end_month:
        return remaining_start, 0

    return remaining_start, (end_month - remaining_start + 1)


def _get_auto_etf_plan(year: int, cfg: dict, start_month: int, end_month: int) -> dict:
    key, target = cfg["key"], cfg["target"]
    actual = _get_actual_etf_total(year, key)
    remaining = max(target - actual, 0)
    rem_start, rem_months = _get_etf_remaining_period(year, key, start_month, end_month)
    monthly_required = ceil_div(remaining, rem_months)
    rate = (actual / target * 100) if target > 0 else 0

    if remaining <= 0:
        status = "🎉 완납"
    elif rem_months <= 0:
        status = "⚠️ 기간 종료"
    else:
        status = "납입 필요"

    return {
        "actual": actual,
        "target": target,
        "remaining": remaining,
        "remaining_start_month": rem_start,
        "remaining_months": rem_months,
        "monthly_required": monthly_required,
        "rate": rate,
        "achievement_rate": min(rate, 100),
        "status": status,
    }


def _get_auto_account_monthly_required(year: int, account: str, start_month: int, end_month: int) -> int:
    return sum(
        _get_auto_etf_plan(year, cfg, start_month, end_month)["monthly_required"]
        for cfg in ETF_CONFIG[account]
    )


def _get_auto_total_monthly_required(year: int, start_month: int, end_month: int) -> int:
    return sum(
        _get_auto_account_monthly_required(year, acc, start_month, end_month)
        for acc in ETF_CONFIG.keys()
    )


def _get_global_auto_remaining_period(year: int, start_month: int, end_month: int):
    base_start = _get_remaining_start_month(year, start_month)
    last_paid_month = 0

    for account in ETF_CONFIG.values():
        for cfg in account:
            last_paid = _get_last_actual_month(year, cfg["key"], start_month, end_month) or 0
            last_paid_month = max(last_paid_month, last_paid)

    remaining_start = max(base_start, last_paid_month + 1) if last_paid_month > 0 else base_start
    if remaining_start > end_month:
        return remaining_start, 0

    return remaining_start, (end_month - remaining_start + 1)


# =========================================================
# Streamlit 데이터 에디터 및 UI 컴포넌트
# =========================================================

def create_account_df(account_name: str, year: int, start_month: int, end_month: int) -> pd.DataFrame:
    month_cols = [f"{m}월" for m in range(1, 13)]
    rows = []

    for cfg in ETF_CONFIG[account_name]:
        monthly_values = _get_etf_monthly_values(year, cfg["key"])
        plan = _get_auto_etf_plan(year, cfg, start_month, end_month)

        row = {
            "ETF종목명": cfg["name"],
            "목표 비중": f"{int(cfg['weight'] * 100)}%",
            "연 목표금액": cfg["target"],
            "자동 월 필요액": plan["monthly_required"],
        }
        for idx, col in enumerate(month_cols):
            row[col] = monthly_values[idx]
        rows.append(row)

    return pd.DataFrame(rows)


def _get_column_config() -> dict:
    config = {
        "ETF종목명": st.column_config.TextColumn("ETF종목명", width="medium"),
        "목표 비중": st.column_config.TextColumn("목표 비중", width="small"),
        "연 목표금액": st.column_config.NumberColumn("연 목표금액", format="%,d원"),
        "자동 월 필요액": st.column_config.NumberColumn("자동 월 필요액", format="%,d원"),
    }
    for m in range(1, 13):
        config[f"{m}월"] = st.column_config.NumberColumn(
            f"{m}월", min_value=0, step=10000, format="%,d원"
        )
    return config


def _update_monthly_data_from_editor(year: int, account: str, edited_df: pd.DataFrame):
    month_cols = [f"{m}월" for m in range(1, 13)]
    for cfg in ETF_CONFIG[account]:
        matched = edited_df[edited_df["ETF종목명"] == cfg["name"]]
        if matched.empty:
            continue
        values = _normalize_monthly_list(matched.iloc[0][month_cols].tolist())
        st.session_state["yearly_data"][year]["monthly_data"][cfg["key"]] = values


def _render_account_editor_section(account: str, icon: str, target_desc: str, year: int, start_month: int,
                                   end_month: int):
    """연금저축 / IRP / ISA 에디터 섹션 공통 렌더링 함수"""
    st.markdown(f"#### {icon} {account} ({target_desc})")

    df = create_account_df(account, year, start_month, end_month)
    edited_df = st.data_editor(
        df,
        key=f"editor_{account}_{year}",
        hide_index=True,
        disabled=["ETF종목명", "목표 비중", "연 목표금액", "자동 월 필요액"],
        column_config=_get_column_config(),
        use_container_width=True,
    )
    _update_monthly_data_from_editor(year, account, edited_df)

    target = sum(cfg["target"] for cfg in ETF_CONFIG[account])
    total = _get_actual_account_total(year, account)
    remaining = max(target - total, 0)
    monthly_req = _get_auto_account_monthly_required(year, account, start_month, end_month)
    rate = (total / target * 100) if target > 0 else 0

    st.info(
        f"{icon} {account} 실제 누적 납입: **{money(total)}** / {money(target)} | "
        f"달성률: **{min(rate, 100):.1f}%** | 남은 금액: **{money(remaining)}** | "
        f"자동 월 필요액: **{money(monthly_req)}**"
    )
    return target, total


def _render_remaining_etf_table(year: int, account: str, start_month: int, end_month: int):
    table_rows = []
    for cfg in ETF_CONFIG[account]:
        plan = _get_auto_etf_plan(year, cfg, start_month, end_month)
        rem_months = plan["remaining_months"]
        period_text = f"{plan['remaining_start_month']}~{end_month}월 ({rem_months}개월)" if rem_months > 0 else "완료"

        table_rows.append({
            "ETF 종목": cfg["name"],
            "목표 비중": f"{int(cfg['weight'] * 100)}%",
            "연간 목표": f"{cfg['target']:,}원",
            "현재 납입": f"{plan['actual']:,}원",
            "남은 금액": f"{plan['remaining']:,}원",
            "남은 기간": period_text,
            "월 필요액": f"{plan['monthly_required']:,}원",
            "달성률": f"{min(plan['rate'], 100):.1f}%",
            "상태": plan["status"],
        })

    st.dataframe(
        pd.DataFrame(table_rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "ETF 종목": st.column_config.TextColumn("ETF 종목", width="large"),
            "목표 비중": st.column_config.TextColumn("목표 비중", width="small"),
            "연간 목표": st.column_config.TextColumn("연간 목표", width="medium"),
            "현재 납입": st.column_config.TextColumn("현재 납입", width="medium"),
            "남은 금액": st.column_config.TextColumn("남은 금액", width="medium"),
            "남은 기간": st.column_config.TextColumn("자동 남은 기간", width="medium"),
            "월 필요액": st.column_config.TextColumn("자동 월 필요액", width="medium"),
            "달성률": st.column_config.TextColumn("달성률", width="small"),
            "상태": st.column_config.TextColumn("상태", width="small"),
        },
    )


def _build_auto_schedule(year: int, start_month: int, end_month: int) -> dict:
    auto_schedule = {m: [] for m in range(start_month, end_month + 1)}

    for account, configs in ETF_CONFIG.items():
        for cfg in configs:
            plan = _get_auto_etf_plan(year, cfg, start_month, end_month)
            remaining, sched_start, months_left = plan["remaining"], plan["remaining_start_month"], plan[
                "remaining_months"]

            if remaining <= 0 or months_left <= 0:
                continue

            base_amount = remaining // months_left
            remainder = remaining % months_left

            for offset in range(months_left):
                m_num = sched_start + offset
                amount = base_amount + (1 if offset < remainder else 0)
                if m_num not in auto_schedule:
                    auto_schedule[m_num] = []
                auto_schedule[m_num].append({"account": account, "name": cfg["name"], "amount": amount})

    return auto_schedule


def _render_auto_schedule(year: int, start_month: int, end_month: int):
    st.subheader(f"📅 {year}년 자동 월별 상세 납입 스케줄")
    st.caption("각 ETF는 실제 마지막 납입월 다음 달부터 남은 목표금액을 자동으로 균등 분배합니다.")

    auto_schedule = _build_auto_schedule(year, start_month, end_month)

    for m_num in range(start_month, end_month + 1):
        items = auto_schedule.get(m_num, [])
        month_total = sum(item["amount"] for item in items)

        with st.expander(f"📅 {year}년 {m_num}월 자동 납입 계획 — {money(month_total)}"):
            if not items:
                st.caption("납입 예정 금액이 없습니다.")
                continue

            for account in ["연금저축", "IRP", "ISA"]:
                acc_items = [item for item in items if item["account"] == account]
                if not acc_items:
                    continue
                st.markdown(f"**{account}**")
                for item in acc_items:
                    st.write(f"• **{item['name']}**: {money(item['amount'])}")


def _build_save_payload() -> dict:
    return {
        str(year): {
            "start_month": st.session_state["yearly_data"][year]["start_month"],
            "end_month": st.session_state["yearly_data"][year]["end_month"],
            "monthly_data": st.session_state["yearly_data"][year]["monthly_data"],
        }
        for year in YEARS
    }


# =========================================================
# 연도별 대시보드 메인
# =========================================================

def _render_year_dashboard(year: int, user_id: str):
    st.subheader(f"📅 {year}년 납입 기간 설정")
    st.success("🔄 자동 재계산 방식: 실제 납입액 입력 시 해당 ETF의 마지막 납입월 기준 자동 재계산됩니다.")

    col1, col2, col3 = st.columns(3)
    start_key, end_key = f"start_month_{year}", f"end_month_{year}"

    if start_key not in st.session_state:
        st.session_state[start_key] = st.session_state["yearly_data"][year]["start_month"]
    if end_key not in st.session_state:
        st.session_state[end_key] = st.session_state["yearly_data"][year]["end_month"]

    with col1:
        start_month = st.number_input("시작월", min_value=1, max_value=12, step=1, key=start_key)
    with col2:
        end_month = st.number_input("종료월", min_value=1, max_value=12, step=1, key=end_key)

    if start_month > end_month:
        st.error("❌ 시작월은 종료월보다 작거나 같아야 합니다.")
        return

    rem_start_month, rem_months = _get_global_auto_remaining_period(year, start_month, end_month)

    with col3:
        st.metric("전체 기준 남은 납입 개월 수", f"{rem_months}개월" if rem_months > 0 else "완료")

    st.session_state["yearly_data"][year]["start_month"] = start_month
    st.session_state["yearly_data"][year]["end_month"] = end_month

    if year == CURRENT_YEAR:
        st.success(
            f"✅ 현재 {CURRENT_MONTH}월 기준입니다. 전체 표시 기준 남은 기간은 "
            f"{rem_start_month}~{end_month}월 총 {rem_months}개월입니다."
        )

    st.divider()

    # 월별 실제 납입액 입력
    st.subheader(f"💵 {year}년 계좌별 월별 실제 납입액 입력")
    st.caption("⚠️ 실제 납입이 완료된 금액만 입력하세요.")

    pension_target, pension_total = _render_account_editor_section(
        "연금저축", "🟢", "연 목표: 6,000,000원", year, start_month, end_month
    )
    irp_target, irp_total = _render_account_editor_section(
        "IRP", "🔵", "연 목표: 3,000,000원", year, start_month, end_month
    )
    isa_target, isa_total = _render_account_editor_section(
        "ISA", "🟠", "연 목표: 3,000,000원", year, start_month, end_month
    )

    # 전체 통계
    actual_total = pension_total + irp_total + isa_total
    annual_target = pension_target + irp_target + isa_target
    actual_remaining = max(annual_target - actual_total, 0)
    actual_monthly_req = _get_auto_total_monthly_required(year, start_month, end_month)
    actual_rate = (actual_total / annual_target * 100) if annual_target > 0 else 0

    st.success(
        f"💰 **{year}년 실제 총 납입액: {money(actual_total)}** = "
        f"연금저축 {money(pension_total)} + IRP {money(irp_total)} + ISA {money(isa_total)}"
    )
    st.divider()

    # 저장 안내 플래그 확인 및 저장 알림 렌더링
    save_status_key = f"save_success_{year}"
    if st.session_state.get(save_status_key):
        st.success(f"✅ **{year}년 납입 계획이 성공적으로 저장되었습니다!**")
        st.session_state[save_status_key] = False

    # 저장 버튼 및 로직
    save_col, _ = st.columns([1, 2])
    with save_col:
        if st.button(f"💾 {year}년 납입 계획 저장하기", type="primary", use_container_width=True, key=f"save_button_{year}"):
            if not user_id:
                st.error("❌ 로그인 정보가 없습니다.")
            else:
                if save_user_plan(user_id, _build_save_payload()):
                    st.toast(f"🎉 {year}년 납입 계획이 저장되었습니다!", icon="💾")
                    st.session_state[save_status_key] = True
                    st.rerun()
                else:
                    st.error("❌ DB 저장에 실패했습니다. 다시 시도해 주세요.")

    st.divider()

    # 현황 지표
    st.subheader(f"🎯 {year}년 자동 재계산 납입 현황")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("연간 총 목표", money(annual_target))
    k2.metric("현재 총 납입액", money(actual_total))
    k3.metric("남은 목표 금액", money(actual_remaining))
    k4.metric("전체 표시 기준", f"{rem_start_month}~{end_month}월" if rem_months > 0 else "완료")
    k5.metric("자동 월 필요 납입액", money(actual_monthly_req))

    progress = actual_total / annual_target if annual_target > 0 else 0
    st.progress(min(max(progress, 0), 1))
    st.caption(f"실제 납입 달성률: **{actual_rate:.2f}%**")

    st.divider()

    # 계좌/ETF별 남은 납입 계획 표
    st.subheader(f"📈 {year}년 계좌/ETF별 남은 납입 계획")
    for account in ["연금저축", "IRP", "ISA"]:
        acc_target = sum(cfg["target"] for cfg in ETF_CONFIG[account])
        acc_current = _get_actual_account_total(year, account)
        acc_remaining = max(acc_target - acc_current, 0)
        acc_monthly_req = _get_auto_account_monthly_required(year, account, start_month, end_month)

        icon = "🟢" if account == "연금저축" else ("🔵" if account == "IRP" else "🟠")

        st.markdown(f"### {icon} {account}")
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("연간 목표", money(acc_target))
        a2.metric("현재 납입", money(acc_current))
        a3.metric("남은 금액", money(acc_remaining))
        a4.metric("자동 월 필요액", money(acc_monthly_req))

        _render_remaining_etf_table(year, account, start_month, end_month)
        st.write("")

    st.divider()

    # 월별 상세 스케줄
    _render_auto_schedule(year, start_month, end_month)


# =========================================================
# 메인 통합 대시보드
# =========================================================

def show_pension_dashboard(user_id=None, cookies=None):
    st.title("💰 통합 자산 납입 계획 (2026 ~ 2030)")
    st.caption("연금저축(600만) + IRP(300만) + ISA(300만) = 연간 1,200만원 기준 납입 계획 관리")

    # DB 로딩 및 세션 상태 관리
    loaded_user_id = st.session_state.get("loaded_user_id")
    if user_id and (loaded_user_id != user_id or "yearly_data" not in st.session_state):
        saved_plan = get_user_plan(user_id)
        st.session_state["yearly_data"] = _migrate_saved_plan(saved_plan)
        st.session_state["loaded_user_id"] = user_id

        # 에디터 관련 세션 상태 초기화
        for year in YEARS:
            st.session_state.pop(f"editor_연금저축_{year}", None)
            st.session_state.pop(f"editor_IRP_{year}", None)
            st.session_state.pop(f"editor_ISA_{year}", None)
            st.session_state.pop(f"start_month_{year}", None)
            st.session_state.pop(f"end_month_{year}", None)

    if "yearly_data" not in st.session_state:
        st.session_state["yearly_data"] = _default_yearly_data()

    # 5개년 총 연간 목표액 (연금저축 600만 + IRP 300만 + ISA 300만 = 1,200만원/년)
    annual_target_all = sum(sum(cfg["target"] for cfg in ETF_CONFIG[acc]) for acc in ETF_CONFIG)
    five_target = annual_target_all * len(YEARS)
    five_actual = sum(_get_actual_total(year) for year in YEARS)
    five_remaining = max(five_target - five_actual, 0)
    five_rate = (five_actual / five_target * 100) if five_target > 0 else 0

    # 5개년 요약
    st.subheader("🗓️ 5개년(2026~2030) 통합 요약")

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("5개년 총 목표", money(five_target))
    s2.metric("5개년 실제 납입", money(five_actual))
    s3.metric("5개년 남은 금액", money(five_remaining))
    s4.metric("5개년 달성률", f"{min(five_rate, 100):.1f}%")

    st.progress(min(max(five_actual / five_target if five_target > 0 else 0, 0), 1))
    st.divider()

    # 연도별 탭
    tabs = st.tabs([f"{year}년" for year in YEARS])
    for tab, year in zip(tabs, YEARS):
        with tab:
            _render_year_dashboard(year, user_id)