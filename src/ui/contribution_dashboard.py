from datetime import date

import pandas as pd
import streamlit as st

from src.db.contribution_dao import (
    get_user_plan,
    save_user_plan,
)


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


CURRENT_YEAR = date.today().year
CURRENT_MONTH = date.today().month


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
        values += [0] * (12 - len(values))

    result = []

    for value in values[:12]:

        try:

            if pd.isna(value):
                result.append(0)

            else:
                result.append(
                    max(int(value), 0)
                )

        except (
            TypeError,
            ValueError,
        ):

            result.append(0)

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

        for key, values in (
            legacy_monthly_data.items()
        ):

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

        saved_year = (
            saved_plan[year_key]
        )

        if not isinstance(
            saved_year,
            dict,
        ):
            continue

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

        if not isinstance(
            saved_monthly_data,
            dict,
        ):
            continue

        for key, values in (
            saved_monthly_data.items()
        ):

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
# 기본 남은 시작월
#
# 현재 연도:
# 현재월까지 실제 납입 완료로 간주
# 다음 달부터 남은 계획 계산
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
# 기본 남은 개월
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
# ETF 월별 실제 납입액
# =========================================================

def _get_etf_monthly_values(
    year,
    etf_key,
):

    yearly_data = (
        st.session_state.get(
            "yearly_data",
            {},
        )
    )

    year_data = yearly_data.get(
        year,
        {},
    )

    monthly_data = (
        year_data.get(
            "monthly_data",
            {},
        )
    )

    return _normalize_monthly_list(
        monthly_data.get(
            etf_key,
            [0] * 12,
        )
    )


# =========================================================
# ETF 실제 납입 총액
# =========================================================

def _get_actual_etf_total(
    year,
    etf_key,
):

    values = _get_etf_monthly_values(
        year,
        etf_key,
    )

    return sum(values)


# =========================================================
# 계좌 실제 납입액
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

    return (
        _get_actual_account_total(
            year,
            "연금저축",
        )
        +
        _get_actual_account_total(
            year,
            "IRP",
        )
    )


# =========================================================
# 마지막 실제 납입월
#
# 예:
#
# 8월  0
# 9월  300,000
# 10월 0
#
# → 마지막 실제 납입월 = 9월
# =========================================================

def _get_last_paid_month(
    year,
    etf_key,
):

    values = _get_etf_monthly_values(
        year,
        etf_key,
    )

    last_month = 0

    for month in range(1, 13):

        if values[month - 1] > 0:

            last_month = month

    return last_month


# =========================================================
# 지정된 기간 내 마지막 실제 납입월
# =========================================================

def _get_last_actual_month(
    year,
    etf_key,
    start_month,
    end_month,
):

    values = _get_etf_monthly_values(
        year,
        etf_key,
    )

    last_month = None

    for month in range(
        start_month,
        end_month + 1,
    ):

        if values[month - 1] > 0:

            last_month = month

    return last_month


# =========================================================
# ETF별 자동 남은 시작월
#
# 핵심 자동 재계산
#
# 현재 8월
# 9월에 실제 납입
#
# → 10월부터 자동 계산
# =========================================================

def _get_etf_remaining_start_month(
    year,
    etf_key,
    start_month,
    end_month,
):

    base_start = (
        _get_remaining_start_month(
            year,
            start_month,
        )
    )

    if base_start > end_month:
        return base_start

    last_actual_month = (
        _get_last_actual_month(
            year,
            etf_key,
            start_month,
            end_month,
        )
    )

    if last_actual_month is None:
        return base_start

    return max(
        base_start,
        last_actual_month + 1,
    )


# =========================================================
# ETF별 자동 남은 기간
# =========================================================

def _get_etf_remaining_period(
    year,
    etf_key,
    start_month,
    end_month,
):

    remaining_start_month = (
        _get_etf_remaining_start_month(
            year,
            etf_key,
            start_month,
            end_month,
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
# ETF 자동 재계산
#
# 가장 중요한 함수
# =========================================================

def _get_auto_etf_plan(
    year,
    cfg,
    start_month,
    end_month,
):

    key = cfg["key"]
    target = cfg["target"]

    # -----------------------------------------------------
    # 실제 납입액
    # -----------------------------------------------------

    actual = _get_actual_etf_total(
        year,
        key,
    )

    # -----------------------------------------------------
    # 목표 대비 남은 금액
    # -----------------------------------------------------

    remaining = max(
        target - actual,
        0,
    )

    # -----------------------------------------------------
    # ETF별 남은 시작월
    # -----------------------------------------------------

    (
        remaining_start_month,
        remaining_months,
    ) = _get_etf_remaining_period(
        year,
        key,
        start_month,
        end_month,
    )

    # -----------------------------------------------------
    # 월 필요액
    # -----------------------------------------------------

    monthly_required = ceil_div(
        remaining,
        remaining_months,
    )

    # -----------------------------------------------------
    # 달성률
    # -----------------------------------------------------

    rate = (
        actual / target * 100
        if target > 0
        else 0
    )

    # -----------------------------------------------------
    # 상태
    # -----------------------------------------------------

    if remaining <= 0:

        status = "🎉 완납"

    elif remaining_months <= 0:

        status = "⚠️ 기간 종료"

    else:

        status = "납입 필요"

    return {
        "actual": actual,
        "actual_total": actual,
        "target": target,
        "remaining": remaining,
        "remaining_amount": remaining,
        "remaining_start_month": (
            remaining_start_month
        ),
        "remaining_months": (
            remaining_months
        ),
        "monthly_required": (
            monthly_required
        ),
        "rate": rate,
        "achievement_rate": min(
            rate,
            100,
        ),
        "status": status,
    }


# =========================================================
# 계좌 자동 월 필요액
#
# ETF마다 남은 기간이 달라도
# 각각 계산한 뒤 합산
# =========================================================

def _get_auto_account_monthly_required(
    year,
    account,
    start_month,
    end_month,
):

    total = 0

    for cfg in ETF_CONFIG[account]:

        plan = _get_auto_etf_plan(
            year,
            cfg,
            start_month,
            end_month,
        )

        total += plan[
            "monthly_required"
        ]

    return total


# =========================================================
# 전체 자동 월 필요액
# =========================================================

def _get_auto_total_monthly_required(
    year,
    start_month,
    end_month,
):

    return (
        _get_auto_account_monthly_required(
            year,
            "연금저축",
            start_month,
            end_month,
        )
        +
        _get_auto_account_monthly_required(
            year,
            "IRP",
            start_month,
            end_month,
        )
    )


# =========================================================
# 전체 자동 남은 기간
#
# 참고용 표시
#
# 실제 계산은 ETF별 기간을 사용한다.
# =========================================================

def _get_global_auto_remaining_period(
    year,
    start_month,
    end_month,
):

    base_start = (
        _get_remaining_start_month(
            year,
            start_month,
        )
    )

    last_paid_month = 0

    for account in ETF_CONFIG.values():

        for cfg in account:

            last_paid_month = max(
                last_paid_month,
                _get_last_actual_month(
                    year,
                    cfg["key"],
                    start_month,
                    end_month,
                )
                or 0,
            )

    if last_paid_month > 0:

        remaining_start = max(
            base_start,
            last_paid_month + 1,
        )

    else:

        remaining_start = base_start

    if (
        remaining_start
        > end_month
    ):

        return (
            remaining_start,
            0,
        )

    return (
        remaining_start,
        end_month
        - remaining_start
        + 1,
    )


# =========================================================
# 계좌별 입력 DataFrame
# =========================================================

def create_account_df(
    account_name,
    year,
    start_month,
    end_month,
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
            _get_etf_monthly_values(
                year,
                key,
            )
        )

        plan = _get_auto_etf_plan(
            year,
            cfg,
            start_month,
            end_month,
        )

        row = {
            "ETF종목명":
                cfg["name"],

            "목표 비중":
                f"{int(cfg['weight'] * 100)}%",

            "연 목표금액":
                cfg["target"],

            "자동 월 필요액":
                plan[
                    "monthly_required"
                ],
        }

        for index, month_col in enumerate(
            month_cols
        ):

            row[month_col] = (
                monthly_values[index]
            )

        rows.append(row)

    return pd.DataFrame(rows)


# =========================================================
# Editor 컬럼 설정
# =========================================================

def _get_column_config():

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

        "자동 월 필요액":
            st.column_config.NumberColumn(
                "자동 월 필요액",
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
# Editor 결과를 Session State에 반영
# =========================================================

def _update_monthly_data_from_editor(
    year,
    account,
    edited_df,
):

    month_cols = [
        f"{month}월"
        for month in range(1, 13)
    ]

    for cfg in ETF_CONFIG[account]:

        matched = edited_df[
            edited_df[
                "ETF종목명"
            ]
            == cfg["name"]
        ]

        if matched.empty:
            continue

        values = (
            matched.iloc[0][
                month_cols
            ].tolist()
        )

        values = (
            _normalize_monthly_list(
                values
            )
        )

        st.session_state[
            "yearly_data"
        ][year][
            "monthly_data"
        ][cfg["key"]] = values


# =========================================================
# 연도별 저장 Payload
# =========================================================

def _build_save_payload():

    payload = {}

    for year in YEARS:

        payload[str(year)] = {

            "start_month":
                st.session_state[
                    "yearly_data"
                ][year][
                    "start_month"
                ],

            "end_month":
                st.session_state[
                    "yearly_data"
                ][year][
                    "end_month"
                ],

            "monthly_data":
                st.session_state[
                    "yearly_data"
                ][year][
                    "monthly_data"
                ],
        }

    return payload


# =========================================================
# 연금저축 요약
# =========================================================

def _render_account_summary(
    year,
    account,
    target,
    icon,
):

    actual = (
        _get_actual_account_total(
            year,
            account,
        )
    )

    remaining = max(
        target - actual,
        0,
    )

    rate = (
        actual / target * 100
        if target > 0
        else 0
    )

    return (
        actual,
        remaining,
        rate,
    )


# =========================================================
# ETF별 남은 납입 표
# =========================================================

def _render_remaining_etf_table(
    year,
    account,
    start_month,
    end_month,
):

    table_rows = []

    for cfg in ETF_CONFIG[
        account
    ]:

        plan = _get_auto_etf_plan(
            year,
            cfg,
            start_month,
            end_month,
        )

        remaining_months = plan[
            "remaining_months"
        ]

        if remaining_months > 0:

            period_text = (
                f"{plan['remaining_start_month']}~"
                f"{end_month}월 "
                f"({remaining_months}개월)"
            )

        else:

            period_text = "완료"

        table_rows.append(
            {
                "ETF 종목":
                    cfg["name"],

                "목표 비중":
                    f"{int(cfg['weight'] * 100)}%",

                "연간 목표":
                    f"{cfg['target']:,}원",

                "현재 납입":
                    f"{plan['actual']:,}원",

                "남은 금액":
                    f"{plan['remaining']:,}원",

                "남은 기간":
                    period_text,

                "월 필요액":
                    f"{plan['monthly_required']:,}원",

                "달성률":
                    f"{min(plan['rate'], 100):.1f}%",

                "상태":
                    plan["status"],
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

            "목표 비중":
                st.column_config.TextColumn(
                    "목표 비중",
                    width="small",
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

            "남은 기간":
                st.column_config.TextColumn(
                    "자동 남은 기간",
                    width="medium",
                ),

            "월 필요액":
                st.column_config.TextColumn(
                    "자동 월 필요액",
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


# =========================================================
# 자동 월별 스케줄 생성
# =========================================================

def _build_auto_schedule(
    year,
    start_month,
    end_month,
):

    auto_schedule = {
        month: []
        for month in range(
            start_month,
            end_month + 1,
        )
    }

    for account, configs in (
        ETF_CONFIG.items()
    ):

        for cfg in configs:

            plan = _get_auto_etf_plan(
                year,
                cfg,
                start_month,
                end_month,
            )

            remaining = plan[
                "remaining"
            ]

            schedule_start = plan[
                "remaining_start_month"
            ]

            months_left = plan[
                "remaining_months"
            ]

            if (
                remaining <= 0
                or months_left <= 0
            ):
                continue

            # -------------------------------------------------
            # 균등 분배
            #
            # 예:
            # 1,000,000 / 3
            #
            # 333,334
            # 333,333
            # 333,333
            #
            # 합계 = 정확히 1,000,000
            # -------------------------------------------------

            base_amount = (
                remaining
                // months_left
            )

            remainder = (
                remaining
                % months_left
            )

            for offset in range(
                months_left
            ):

                month_number = (
                    schedule_start
                    + offset
                )

                amount = (
                    base_amount
                    + (
                        1
                        if offset < remainder
                        else 0
                    )
                )

                if month_number not in (
                    auto_schedule
                ):
                    auto_schedule[
                        month_number
                    ] = []

                auto_schedule[
                    month_number
                ].append(
                    {
                        "account":
                            account,

                        "name":
                            cfg["name"],

                        "amount":
                            amount,
                    }
                )

    return auto_schedule


# =========================================================
# 자동 월별 스케줄 화면
# =========================================================

def _render_auto_schedule(
    year,
    start_month,
    end_month,
):

    st.subheader(
        f"📅 {year}년 자동 월별 상세 납입 스케줄"
    )

    st.caption(
        "각 ETF는 실제 마지막 납입월 다음 달부터 "
        "남은 목표금액을 자동으로 균등 분배합니다. "
        "실제 납입액을 수정하면 자동으로 다시 계산됩니다."
    )

    auto_schedule = (
        _build_auto_schedule(
            year,
            start_month,
            end_month,
        )
    )

    for month_number in range(
        start_month,
        end_month + 1,
    ):

        items = auto_schedule.get(
            month_number,
            [],
        )

        month_total = sum(
            item["amount"]
            for item in items
        )

        with st.expander(
            f"📅 {year}년 "
            f"{month_number}월 자동 납입 계획 — "
            f"{money(month_total)}"
        ):

            if not items:

                st.caption(
                    "납입 예정 금액이 없습니다."
                )

                continue

            for account in [
                "연금저축",
                "IRP",
            ]:

                account_items = [
                    item
                    for item in items
                    if item["account"]
                    == account
                ]

                if not account_items:
                    continue

                st.markdown(
                    f"**{account}**"
                )

                for item in account_items:

                    st.write(
                        f"• **{item['name']}**: "
                        f"{money(item['amount'])}"
                    )


# =========================================================
# 연도 Dashboard
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

    st.success(
        "🔄 자동 재계산 방식: 실제 납입액을 입력하면 "
        "해당 ETF의 마지막 실제 납입월을 기준으로 "
        "남은 기간과 월 필요액을 자동으로 다시 계산합니다."
    )

    col1, col2, col3 = st.columns(3)

    start_key = (
        f"start_month_{year}"
    )

    end_key = (
        f"end_month_{year}"
    )

    if start_key not in st.session_state:

        st.session_state[
            start_key
        ] = st.session_state[
            "yearly_data"
        ][year][
            "start_month"
        ]

    if end_key not in st.session_state:

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

    if start_month > end_month:

        st.error(
            "❌ 시작월은 종료월보다 작거나 같아야 합니다."
        )

        return

    (
        remaining_start_month,
        remaining_months,
    ) = _get_global_auto_remaining_period(
        year,
        start_month,
        end_month,
    )

    with col3:

        st.metric(
            "전체 기준 남은 납입 개월 수",
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
            f"✅ 현재 {CURRENT_MONTH}월 기준입니다. "
            f"전체 표시 기준 남은 기간은 "
            f"{remaining_start_month}~{end_month}월 "
            f"총 {remaining_months}개월입니다. "
            "단, 실제 계산은 ETF별 마지막 납입월을 "
            "기준으로 각각 자동 계산됩니다."
        )

    st.divider()

    # =====================================================
    # 월별 입력
    # =====================================================

    st.subheader(
        f"💵 {year}년 계좌별 월별 실제 납입액 입력"
    )

    st.caption(
        "⚠️ 실제 납입이 완료된 금액만 입력하세요. "
        "예를 들어 9월에 실제 납입한 금액을 입력하면 "
        "해당 ETF는 10월부터 남은 목표금액을 자동 재계산합니다."
    )

    # =====================================================
    # 연금저축
    # =====================================================

    df_pension = create_account_df(
        "연금저축",
        year,
        start_month,
        end_month,
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
            "자동 월 필요액",
        ],
        column_config=_get_column_config(),
        use_container_width=True,
    )

    _update_monthly_data_from_editor(
        year,
        "연금저축",
        edited_pension_df,
    )

    pension_target = (
        sum(
            cfg["target"]
            for cfg in ETF_CONFIG[
                "연금저축"
            ]
        )
    )

    pension_total = (
        _get_actual_account_total(
            year,
            "연금저축",
        )
    )

    pension_remaining = max(
        pension_target
        - pension_total,
        0,
    )

    pension_monthly_required = (
        _get_auto_account_monthly_required(
            year,
            "연금저축",
            start_month,
            end_month,
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
        f"자동 월 필요액: "
        f"**{money(pension_monthly_required)}**"
    )

    # =====================================================
    # IRP
    # =====================================================

    st.markdown(
        "#### 🔵 IRP "
        "(연 목표: 3,000,000원)"
    )

    df_irp = create_account_df(
        "IRP",
        year,
        start_month,
        end_month,
    )

    edited_irp_df = st.data_editor(
        df_irp,
        key=f"editor_irp_{year}",
        hide_index=True,
        disabled=[
            "ETF종목명",
            "목표 비중",
            "연 목표금액",
            "자동 월 필요액",
        ],
        column_config=_get_column_config(),
        use_container_width=True,
    )

    _update_monthly_data_from_editor(
        year,
        "IRP",
        edited_irp_df,
    )

    irp_target = (
        sum(
            cfg["target"]
            for cfg in ETF_CONFIG[
                "IRP"
            ]
        )
    )

    irp_total = (
        _get_actual_account_total(
            year,
            "IRP",
        )
    )

    irp_remaining = max(
        irp_target
        - irp_total,
        0,
    )

    irp_monthly_required = (
        _get_auto_account_monthly_required(
            year,
            "IRP",
            start_month,
            end_month,
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
        f"자동 월 필요액: "
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
        _get_auto_total_monthly_required(
            year,
            start_month,
            end_month,
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

                payload = (
                    _build_save_payload()
                )

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
    # 자동 재계산 현황
    # =====================================================

    st.subheader(
        f"🎯 {year}년 자동 재계산 납입 현황"
    )

    k1, k2, k3, k4, k5 = (
        st.columns(5)
    )

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
            "전체 표시 기준",
            (
                f"{remaining_start_month}~"
                f"{end_month}월"
                if remaining_months > 0
                else "완료"
            ),
        )

    with k5:

        st.metric(
            "자동 월 필요 납입액",
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
        f"계좌/ETF별 남은 납입 계획"
    )

    st.caption(
        "각 ETF의 실제 납입 현황을 기준으로 "
        "마지막 납입월 다음 달부터 남은 목표금액을 "
        "자동 계산합니다."
    )

    st.info(
        "🔄 **자동 재계산 ON**\n\n"
        "예: 9월에 S&P500에 300,000원을 실제 납입하면 "
        "S&P500의 남은 금액과 10~12월 월 필요액이 "
        "자동으로 다시 계산됩니다."
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
            _get_auto_account_monthly_required(
                year,
                account,
                start_month,
                end_month,
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

        a1, a2, a3, a4 = (
            st.columns(4)
        )

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
                "자동 월 필요액",
                money(
                    account_monthly_required
                ),
            )

        _render_remaining_etf_table(
            year,
            account,
            start_month,
            end_month,
        )

        st.write("")

    st.divider()

    # =====================================================
    # 월별 상세 자동 납입 스케줄
    # =====================================================

    _render_auto_schedule(
        year,
        start_month,
        end_month,
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
            loaded_user_id != user_id
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

        # -------------------------------------------------
        # 기존 editor 상태 제거
        # -------------------------------------------------

        for year in YEARS:

            st.session_state.pop(
                f"editor_pension_{year}",
                None,
            )

            st.session_state.pop(
                f"editor_irp_{year}",
                None,
            )

            st.session_state.pop(
                f"start_month_{year}",
                None,
            )

            st.session_state.pop(
                f"end_month_{year}",
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

    s1, s2, s3, s4 = (
        st.columns(4)
    )

    with s1:

        st.metric(
            "5개년 총 목표",
            money(
                five_year_target
            ),
        )

    with s2:

        st.metric(
            "5개년 실제 납입",
            money(
                five_year_actual
            ),
        )

    with s3:

        st.metric(
            "5개년 남은 금액",
            money(
                five_year_remaining
            ),
        )

    with s4:

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