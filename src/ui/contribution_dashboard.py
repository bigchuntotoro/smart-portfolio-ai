import pandas as pd
import streamlit as st

from src.core.contribution_plan import (
    ContributionItem,
    build_monthly_schedule,
    calculate_contribution_plan,
    calculate_remaining_plan,
)
from src.db.contribution_dao import get_user_plan, save_user_plan


# =========================================================
# 금액 표시
# =========================================================

def money(value):
    return f"{int(value):,}원"


# =========================================================
# 나눗셈 올림
# =========================================================

def ceil_div(value, divisor):
    if divisor <= 0:
        return 0

    if value <= 0:
        return 0

    return (value + divisor - 1) // divisor


# =========================================================
# ETF 설정
# =========================================================

ETF_CONFIG = {
    "연금저축": [
        {
            "key": "p_sp500",
            "name": "TIGER 미국S&P500",
            "target": 1_500_000,
            "weight": 0.25,
        },
        {
            "key": "p_nasdaq",
            "name": "KODEX 미국나스닥100",
            "target": 1_500_000,
            "weight": 0.25,
        },
        {
            "key": "p_dividend",
            "name": "KODEX 미국배당다우존스",
            "target": 3_000_000,
            "weight": 0.50,
        },
    ],

    "IRP": [
        {
            "key": "i_high_div",
            "name": "KODEX 주주환원고배당주",
            "target": 900_000,
            "weight": 0.30,
        },
        {
            "key": "i_cover_call",
            "name": "KODEX 200타겟위클리커버드콜",
            "target": 1_200_000,
            "weight": 0.40,
        },
        {
            "key": "i_bond",
            "name": "KODEX 단기채권PLUS",
            "target": 900_000,
            "weight": 0.30,
        },
    ],
}


# =========================================================
# 연도
# =========================================================

YEARS = [
    2026,
    2027,
    2028,
    2029,
    2030,
]


CURRENT_YEAR = 2026
CURRENT_MONTH = 8


# =========================================================
# 기본 월별 데이터
# =========================================================

def _default_monthly_data():

    return {
        cfg["key"]: [0] * 12
        for account in ETF_CONFIG.values()
        for cfg in account
    }


# =========================================================
# 기본 연도 데이터
# =========================================================

def _default_yearly_data():

    yearly_data = {}

    for year in YEARS:

        if year == 2026:

            start_month = 8
            end_month = 12

        else:

            start_month = 1
            end_month = 12

        yearly_data[year] = {
            "start_month": start_month,
            "end_month": end_month,
            "monthly_data": _default_monthly_data(),
        }

    return yearly_data


# =========================================================
# 월 데이터 정규화
# =========================================================

def _normalize_monthly_list(values):

    if values is None:
        values = []

    values = list(values)

    if len(values) < 12:

        values += [
            0
        ] * (
            12 - len(values)
        )

    result = []

    for value in values[:12]:

        if pd.isna(value):

            result.append(0)

        else:

            result.append(
                int(value)
            )

    return result


# =========================================================
# 기존 DB 데이터 변환
# =========================================================

def _migrate_saved_plan(saved_plan):

    yearly_data = _default_yearly_data()

    if not saved_plan:

        return yearly_data

    # -----------------------------------------------------
    # 기존 단일연도 데이터
    # -----------------------------------------------------

    if (
        "monthly_data" in saved_plan
        and "start_month" in saved_plan
    ):

        yearly_data[2026][
            "start_month"
        ] = saved_plan.get(
            "start_month",
            8,
        )

        yearly_data[2026][
            "end_month"
        ] = saved_plan.get(
            "end_month",
            12,
        )

        legacy_monthly_data = (
            saved_plan.get(
                "monthly_data",
                {},
            )
        )

        for key, values in legacy_monthly_data.items():

            if (
                key
                in yearly_data[2026][
                    "monthly_data"
                ]
            ):

                yearly_data[2026][
                    "monthly_data"
                ][key] = (
                    _normalize_monthly_list(
                        values
                    )
                )

        return yearly_data

    # -----------------------------------------------------
    # 연도별 데이터
    # -----------------------------------------------------

    for year in YEARS:

        year_key = str(year)

        if year_key not in saved_plan:

            continue

        saved_year = saved_plan[
            year_key
        ]

        yearly_data[year][
            "start_month"
        ] = saved_year.get(
            "start_month",
            yearly_data[year][
                "start_month"
            ],
        )

        yearly_data[year][
            "end_month"
        ] = saved_year.get(
            "end_month",
            yearly_data[year][
                "end_month"
            ],
        )

        saved_monthly_data = (
            saved_year.get(
                "monthly_data",
                {},
            )
        )

        for key, values in saved_monthly_data.items():

            if (
                key
                in yearly_data[year][
                    "monthly_data"
                ]
            ):

                yearly_data[year][
                    "monthly_data"
                ][key] = (
                    _normalize_monthly_list(
                        values
                    )
                )

    return yearly_data


# =========================================================
# 남은 시작월
# =========================================================

def _get_remaining_start_month(
    year,
    start_month,
):

    if year == CURRENT_YEAR:

        return max(
            start_month,
            CURRENT_MONTH + 1,
        )

    return start_month


# =========================================================
# 남은 개월
# =========================================================

def _get_remaining_months(
    year,
    start_month,
    end_month,
):

    remaining_start_month = (
        _get_remaining_start_month(
            year,
            start_month,
        )
    )

    if (
        remaining_start_month
        > end_month
    ):

        return (
            remaining_start_month,
            0,
        )

    remaining_months = (
        end_month
        - remaining_start_month
        + 1
    )

    return (
        remaining_start_month,
        remaining_months,
    )


# =========================================================
# ETF 실제 납입액
#
# ★ 월별 입력값이 원본
# =========================================================

def _get_actual_etf_total(
    year,
    etf_key,
):

    monthly_data = (
        st.session_state[
            "yearly_data"
        ][year]["monthly_data"]
    )

    values = _normalize_monthly_list(
        monthly_data.get(
            etf_key,
            [0] * 12,
        )
    )

    return sum(values)


# =========================================================
# 계좌 실제 납입액
#
# ★ 월별 입력값 직접 합산
# =========================================================

def _get_actual_account_total(
    year,
    account,
):

    total = 0

    for cfg in ETF_CONFIG[account]:

        total += _get_actual_etf_total(
            year,
            cfg["key"],
        )

    return total


# =========================================================
# 전체 실제 납입액
# =========================================================

def _get_actual_total(year):

    pension_total = (
        _get_actual_account_total(
            year,
            "연금저축",
        )
    )

    irp_total = (
        _get_actual_account_total(
            year,
            "IRP",
        )
    )

    return (
        pension_total
        + irp_total
    )


# =========================================================
# ETF 입력 데이터프레임
# =========================================================

def create_account_df(
    account_name,
    year,
    remaining_months,
):

    month_cols = [
        f"{month}월"
        for month in range(1, 13)
    ]

    rows = []

    for cfg in ETF_CONFIG[
        account_name
    ]:

        key = cfg["key"]

        monthly_values = (
            _normalize_monthly_list(
                st.session_state[
                    "yearly_data"
                ][year][
                    "monthly_data"
                ].get(
                    key,
                    [0] * 12,
                )
            )
        )

        actual_total = sum(
            monthly_values
        )

        remaining_amount = max(
            cfg["target"]
            - actual_total,
            0,
        )

        monthly_required = ceil_div(
            remaining_amount,
            remaining_months,
        )

        row = {

            "ETF종목명":
                cfg["name"],

            "목표 비중":
                f"{int(cfg['weight'] * 100)}%",

            "연 목표금액":
                cfg["target"],

            "월 기준금액(남은 기간)":
                monthly_required,
        }

        for index, month_col in enumerate(
            month_cols
        ):

            row[
                month_col
            ] = monthly_values[index]

        rows.append(row)

    return pd.DataFrame(
        rows
    )


# =========================================================
# Editor 컬럼
# =========================================================

def _get_column_config(
    remaining_months,
):

    month_cols = [
        f"{month}월"
        for month in range(1, 13)
    ]

    config = {

        "ETF종목명":
            st.column_config.TextColumn(
                "ETF종목명",
                width="medium",
            ),

        "목표 비중":
            st.column_config.TextColumn(
                "목표 비중",
                width="small",
            ),

        "연 목표금액":
            st.column_config.NumberColumn(
                "연 목표금액",
                format="%,d원",
            ),

        "월 기준금액(남은 기간)":
            st.column_config.NumberColumn(
                f"월 기준금액({remaining_months}개월)",
                format="%,d원",
            ),
    }

    for month_col in month_cols:

        config[
            month_col
        ] = st.column_config.NumberColumn(
            month_col,
            min_value=0,
            step=10000,
            format="%,d원",
        )

    return config


# =========================================================
# 연도 화면
# =========================================================

def _render_year_dashboard(
    year,
    user_id,
):

    month_cols = [
        f"{month}월"
        for month in range(1, 13)
    ]

    # =====================================================
    # 납입 기간
    # =====================================================

    st.subheader(
        f"📅 {year}년 납입 기간 설정"
    )

    col1, col2, col3 = st.columns(3)

    start_key = (
        f"start_month_{year}"
    )

    end_key = (
        f"end_month_{year}"
    )

    if (
        start_key
        not in st.session_state
    ):

        st.session_state[
            start_key
        ] = st.session_state[
            "yearly_data"
        ][year][
            "start_month"
        ]

    if (
        end_key
        not in st.session_state
    ):

        st.session_state[
            end_key
        ] = st.session_state[
            "yearly_data"
        ][year][
            "end_month"
        ]

    with col1:

        start_month = st.number_input(
            "시작월",
            min_value=1,
            max_value=12,
            step=1,
            key=start_key,
        )

    with col2:

        end_month = st.number_input(
            "종료월",
            min_value=1,
            max_value=12,
            step=1,
            key=end_key,
        )

    if (
        start_month
        > end_month
    ):

        st.error(
            "❌ 시작월은 종료월보다 작거나 같아야 합니다."
        )

        return

    (
        remaining_start_month,
        remaining_months,
    ) = _get_remaining_months(
        year,
        start_month,
        end_month,
    )

    with col3:

        st.metric(
            "남은 납입 개월 수",
            (
                f"{remaining_months}개월"
                if remaining_months > 0
                else "완료"
            ),
        )

    st.session_state[
        "yearly_data"
    ][year][
        "start_month"
    ] = start_month

    st.session_state[
        "yearly_data"
    ][year][
        "end_month"
    ] = end_month

    if year == CURRENT_YEAR:

        st.success(
            f"✅ {CURRENT_MONTH}월까지 납입 완료 기준입니다. "
            f"실제 남은 납입기간은 "
            f"{remaining_start_month}~{end_month}월 "
            f"총 {remaining_months}개월입니다."
        )

    st.divider()

    # =====================================================
    # 계좌별 월별 입력
    # =====================================================

    st.subheader(
        f"💵 {year}년 계좌별 월별 납입액 입력"
    )

    st.caption(
        "⚠️ 이 화면에 입력한 월별 납입액이 "
        "실제 납입액의 기준입니다."
    )

    # =====================================================
    # 연금저축
    # =====================================================

    df_pension = create_account_df(
        "연금저축",
        year,
        remaining_months,
    )

    st.markdown(
        "#### 🟢 연금저축 "
        "(연 목표: 6,000,000원)"
    )

    edited_pension_df = st.data_editor(
        df_pension,
        key=f"editor_pension_{year}",
        hide_index=True,
        disabled=[
            "ETF종목명",
            "목표 비중",
            "연 목표금액",
            "월 기준금액(남은 기간)",
        ],
        column_config=_get_column_config(
            remaining_months
        ),
        use_container_width=True,
    )

    for cfg in ETF_CONFIG[
        "연금저축"
    ]:

        matched = edited_pension_df[
            edited_pension_df[
                "ETF종목명"
            ]
            == cfg["name"]
        ]

        if matched.empty:

            continue

        values = _normalize_monthly_list(
            matched.iloc[0][
                month_cols
            ].tolist()
        )

        st.session_state[
            "yearly_data"
        ][year][
            "monthly_data"
        ][cfg["key"]] = values

    pension_total = (
        _get_actual_account_total(
            year,
            "연금저축",
        )
    )

    pension_target = 6_000_000

    pension_remaining = max(
        pension_target
        - pension_total,
        0,
    )

    pension_monthly_required = (
        ceil_div(
            pension_remaining,
            remaining_months,
        )
    )

    pension_rate = (
        pension_total
        / pension_target
        * 100
        if pension_target > 0
        else 0
    )

    st.info(
        f"🟢 연금저축 실제 누적 납입: "
        f"**{money(pension_total)}** / "
        f"{money(pension_target)} | "
        f"달성률: **{min(pension_rate, 100):.1f}%** | "
        f"남은 금액: **{money(pension_remaining)}** | "
        f"남은 {remaining_months}개월 월 필요액: "
        f"**{money(pension_monthly_required)}**"
    )

    st.write("")

    # =====================================================
    # IRP
    # =====================================================

    df_irp = create_account_df(
        "IRP",
        year,
        remaining_months,
    )

    st.markdown(
        "#### 🔵 IRP "
        "(연 목표: 3,000,000원)"
    )

    edited_irp_df = st.data_editor(
        df_irp,
        key=f"editor_irp_{year}",
        hide_index=True,
        disabled=[
            "ETF종목명",
            "목표 비중",
            "연 목표금액",
            "월 기준금액(남은 기간)",
        ],
        column_config=_get_column_config(
            remaining_months
        ),
        use_container_width=True,
    )

    for cfg in ETF_CONFIG[
        "IRP"
    ]:

        matched = edited_irp_df[
            edited_irp_df[
                "ETF종목명"
            ]
            == cfg["name"]
        ]

        if matched.empty:

            continue

        values = _normalize_monthly_list(
            matched.iloc[0][
                month_cols
            ].tolist()
        )

        st.session_state[
            "yearly_data"
        ][year][
            "monthly_data"
        ][cfg["key"]] = values

    # ★★★ IRP 실제 납입액
    # 월별 입력값에서 직접 계산
    irp_total = (
        _get_actual_account_total(
            year,
            "IRP",
        )
    )

    irp_target = 3_000_000

    irp_remaining = max(
        irp_target
        - irp_total,
        0,
    )

    irp_monthly_required = (
        ceil_div(
            irp_remaining,
            remaining_months,
        )
    )

    irp_rate = (
        irp_total
        / irp_target
        * 100
        if irp_target > 0
        else 0
    )

    st.info(
        f"🔵 IRP 실제 누적 납입: "
        f"**{money(irp_total)}** / "
        f"{money(irp_target)} | "
        f"달성률: **{min(irp_rate, 100):.1f}%** | "
        f"남은 금액: **{money(irp_remaining)}** | "
        f"남은 {remaining_months}개월 월 필요액: "
        f"**{money(irp_monthly_required)}**"
    )

    # =====================================================
    # 전체 실제 납입
    # =====================================================

    actual_total = (
        pension_total
        + irp_total
    )

    annual_target = (
        pension_target
        + irp_target
    )

    actual_remaining = max(
        annual_target
        - actual_total,
        0,
    )

    actual_monthly_required = (
        ceil_div(
            actual_remaining,
            remaining_months,
        )
    )

    actual_rate = (
        actual_total
        / annual_target
        * 100
        if annual_target > 0
        else 0
    )

    st.success(
        f"💰 **{year}년 실제 총 납입액: "
        f"{money(actual_total)}** "
        f"= 연금저축 {money(pension_total)} "
        f"+ IRP {money(irp_total)}"
    )

    st.divider()

    # =====================================================
    # 저장
    # =====================================================

    save_col, _ = st.columns(
        [1, 2]
    )

    with save_col:

        if st.button(
            f"💾 {year}년 납입 계획 저장하기",
            type="primary",
            use_container_width=True,
            key=f"save_button_{year}",
        ):

            if not user_id:

                st.error(
                    "❌ 로그인 정보가 없습니다."
                )

            else:

                payload = {
                    str(y): {
                        "start_month":
                            st.session_state[
                                "yearly_data"
                            ][y][
                                "start_month"
                            ],

                        "end_month":
                            st.session_state[
                                "yearly_data"
                            ][y][
                                "end_month"
                            ],

                        "monthly_data":
                            st.session_state[
                                "yearly_data"
                            ][y][
                                "monthly_data"
                            ],
                    }
                    for y in YEARS
                }

                success = save_user_plan(
                    user_id,
                    payload,
                )

                if success:

                    st.success(
                        f"✅ {year}년 납입 계획이 저장되었습니다."
                    )

                else:

                    st.error(
                        "❌ DB 저장에 실패했습니다."
                    )

    st.divider()

    # =====================================================
    # 남은 납입 현황
    # =====================================================

    st.subheader(
        f"🎯 {year}년 남은 "
        f"{remaining_months}개월 "
        f"납입 현황 및 필요 기준액"
    )

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:

        st.metric(
            "연간 총 목표",
            money(annual_target),
        )

    with k2:

        st.metric(
            "현재 총 납입액",
            money(actual_total),
        )

    with k3:

        st.metric(
            "남은 목표 금액",
            money(actual_remaining),
        )

    with k4:

        st.metric(
            "남은 기간",
            f"{remaining_months}개월",
        )

    with k5:

        st.metric(
            "월 필요 납입액",
            money(actual_monthly_required),
        )

    progress = (
        actual_total
        / annual_target
        if annual_target > 0
        else 0
    )

    st.progress(
        min(
            max(progress, 0),
            1,
        )
    )

    st.caption(
        f"실제 납입 달성률: "
        f"**{actual_rate:.2f}%**"
    )

    st.divider()

    # =====================================================
    # 계좌 / ETF별 남은 납입 계획
    # =====================================================

    st.subheader(
        f"📈 {year}년 "
        f"{remaining_start_month}~{end_month}월 "
        f"계좌/ETF별 남은 납입 계획"
    )

    st.caption(
        "현재 납입액은 위의 '계좌별 월별 납입액 입력' "
        "값을 직접 합산합니다."
    )

    # =====================================================
    # 계산용 ContributionItem
    # =====================================================

    all_items = []

    for account, configs in ETF_CONFIG.items():

        for cfg in configs:

            actual_etf_total = (
                _get_actual_etf_total(
                    year,
                    cfg["key"],
                )
            )

            all_items.append(
                ContributionItem(
                    account=account,
                    name=cfg["name"],
                    annual_target=cfg["target"],
                    weight=cfg["weight"],
                    current_amount=actual_etf_total,
                )
            )

    calculated_items = (
        calculate_contribution_plan(
            all_items
        )
    )

    plan = calculate_remaining_plan(
        calculated_items,
        remaining_start_month,
        end_month,
    )

    # =====================================================
    # 계좌별 표
    # =====================================================

    for account in [
        "연금저축",
        "IRP",
    ]:

        account_target = sum(
            cfg["target"]
            for cfg in ETF_CONFIG[
                account
            ]
        )

        # ★ 월별 입력값에서 직접 계산
        account_current = (
            _get_actual_account_total(
                year,
                account,
            )
        )

        account_remaining = max(
            account_target
            - account_current,
            0,
        )

        account_monthly_required = (
            ceil_div(
                account_remaining,
                remaining_months,
            )
        )

        icon = (
            "🟢"
            if account == "연금저축"
            else "🔵"
        )

        st.markdown(
            f"### {icon} {account}"
        )

        a1, a2, a3, a4 = st.columns(4)

        with a1:

            st.metric(
                "연간 목표",
                money(account_target),
            )

        with a2:

            st.metric(
                "현재 납입",
                money(account_current),
            )

        with a3:

            st.metric(
                "남은 금액",
                money(account_remaining),
            )

        with a4:

            st.metric(
                f"월 필요액 ({remaining_months}개월)",
                money(account_monthly_required),
            )

        # =================================================
        # ★ ETF 표
        # =================================================

        table_rows = []

        for cfg in ETF_CONFIG[
            account
        ]:

            # ★ 월별 입력값을 직접 합산
            etf_current = (
                _get_actual_etf_total(
                    year,
                    cfg["key"],
                )
            )

            etf_target = cfg[
                "target"
            ]

            etf_remaining = max(
                etf_target
                - etf_current,
                0,
            )

            etf_monthly = ceil_div(
                etf_remaining,
                remaining_months,
            )

            etf_rate = (
                etf_current
                / etf_target
                * 100
                if etf_target > 0
                else 0
            )

            status = (
                "🎉 완납"
                if etf_remaining <= 0
                else "납입 필요"
            )

            table_rows.append(
                {
                    "ETF 종목":
                        cfg["name"],

                    "연간 목표":
                        f"{etf_target:,}원",

                    "현재 납입":
                        f"{etf_current:,}원",

                    "남은 금액":
                        f"{etf_remaining:,}원",

                    "월 필요액":
                        f"{etf_monthly:,}원",

                    "달성률":
                        f"{min(etf_rate, 100):.1f}%",

                    "상태":
                        status,
                }
            )

        table_df = pd.DataFrame(
            table_rows
        )

        st.dataframe(
            table_df,
            hide_index=True,
            use_container_width=True,
            column_config={

                "ETF 종목":
                    st.column_config.TextColumn(
                        "ETF 종목",
                        width="large",
                    ),

                "연간 목표":
                    st.column_config.TextColumn(
                        "연간 목표",
                        width="medium",
                    ),

                "현재 납입":
                    st.column_config.TextColumn(
                        "현재 납입",
                        width="medium",
                    ),

                "남은 금액":
                    st.column_config.TextColumn(
                        "남은 금액",
                        width="medium",
                    ),

                "월 필요액":
                    st.column_config.TextColumn(
                        f"{remaining_start_month}~"
                        f"{end_month}월 "
                        "월 필요액",
                        width="medium",
                    ),

                "달성률":
                    st.column_config.TextColumn(
                        "달성률",
                        width="small",
                    ),

                "상태":
                    st.column_config.TextColumn(
                        "상태",
                        width="small",
                    ),
            },
        )

        st.write("")

    st.divider()

    # =====================================================
    # 월별 상세 스케줄
    # =====================================================

    st.subheader(
        f"📅 {year}년 "
        f"{remaining_start_month}~{end_month}월 "
        f"월별 상세 납입 스케줄"
    )

    schedule = build_monthly_schedule(
        plan,
        remaining_start_month,
        end_month,
    )

    for month_data in schedule:

        month_number = (
            month_data["month"]
        )

        month_total = (
            month_data["total"]
        )

        with st.expander(
            f"📅 {year}년 "
            f"{month_number}월 납입 계획 — "
            f"{money(month_total)}"
        ):

            for item in month_data[
                "items"
            ]:

                if item["amount"] > 0:

                    st.write(
                        f"• **{item['name']}**: "
                        f"{money(item['amount'])}"
                    )


# =========================================================
# 메인 화면
# =========================================================

def show_pension_dashboard(
    user_id=None,
    cookies=None,
):

    st.title(
        "💰 통합 연금 납입 계획 "
        "(2026 ~ 2030)"
    )

    st.caption(
        "연금저축 600만원 + IRP 300만원 = "
        "연간 900만원을 기준으로 "
        "2026~2030년 납입 계획을 관리합니다."
    )

    # =====================================================
    # DB 로딩
    # =====================================================

    loaded_user_id = (
        st.session_state.get(
            "loaded_user_id"
        )
    )

    if (
        user_id
        and (
            loaded_user_id
            != user_id
            or "yearly_data"
            not in st.session_state
        )
    ):

        saved_plan = get_user_plan(
            user_id
        )

        st.session_state[
            "yearly_data"
        ] = _migrate_saved_plan(
            saved_plan
        )

        st.session_state[
            "loaded_user_id"
        ] = user_id

        for year in YEARS:

            st.session_state.pop(
                f"editor_pension_{year}",
                None,
            )

            st.session_state.pop(
                f"editor_irp_{year}",
                None,
            )

    # =====================================================
    # 기본 데이터
    # =====================================================

    if (
        "yearly_data"
        not in st.session_state
    ):

        st.session_state[
            "yearly_data"
        ] = _default_yearly_data()

    # =====================================================
    # 5개년 요약
    # =====================================================

    st.subheader(
        "🗓️ 5개년(2026~2030) 통합 요약"
    )

    five_year_target = (
        9_000_000
        * len(YEARS)
    )

    five_year_actual = 0

    for year in YEARS:

        five_year_actual += (
            _get_actual_total(
                year
            )
        )

    five_year_remaining = max(
        five_year_target
        - five_year_actual,
        0,
    )

    five_year_rate = (
        five_year_actual
        / five_year_target
        * 100
        if five_year_target > 0
        else 0
    )

    s1, s2, s3 = st.columns(3)

    with s1:

        st.metric(
            "5개년 총 목표",
            money(five_year_target),
        )

    with s2:

        st.metric(
            "5개년 실제 납입",
            money(five_year_actual),
        )

    with s3:

        st.metric(
            "5개년 달성률",
            f"{min(five_year_rate, 100):.1f}%",
        )

    five_progress = (
        five_year_actual
        / five_year_target
        if five_year_target > 0
        else 0
    )

    st.progress(
        min(
            max(
                five_progress,
                0,
            ),
            1,
        )
    )

    st.divider()

    # =====================================================
    # 연도별 탭
    # =====================================================

    tabs = st.tabs(
        [
            f"{year}년"
            for year in YEARS
        ]
    )

    for tab, year in zip(
        tabs,
        YEARS,
    ):

        with tab:

            _render_year_dashboard(
                year,
                user_id,
            )