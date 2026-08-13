import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from src.core.portfolio import calculate_buy_only_rebalancing
from src.db.contribution_dao import get_user_plan

# =========================================================
# DB 매핑용 ETF 정보 및 목표 비중 정의 (전체 900만원 통합 기준)
# - 연금저축(600만 원 / 66.7%): S&P500(16.67%), 나스닥(16.67%), 배당다우(33.33%)
# - IRP(300만 원 / 33.3%): 고배당주(10.0%), 커버드콜(13.33%), 단기채권(10.0%)
# =========================================================
ETF_CONFIG = [
    {
        "key": "p_sp500",
        "account": "연금저축",
        "name": "TIGER 미국S&P500",
        "target_weight": 0.1667,  # 16.67% (66.7% x 25%)
        "default_val": 1_500_000,
    },
    {
        "key": "p_nasdaq",
        "account": "연금저축",
        "name": "KODEX 미국나스닥100",
        "target_weight": 0.1667,  # 16.67% (66.7% x 25%)
        "default_val": 1_500_000,
    },
    {
        "key": "p_dividend",
        "account": "연금저축",
        "name": "KODEX 미국배당다우존스",
        "target_weight": 0.3333,  # 33.33% (66.7% x 50%)
        "default_val": 3_000_000,
    },
    {
        "key": "i_high_div",
        "account": "IRP",
        "name": "KODEX 주주환원고배당주",
        "target_weight": 0.1000,  # 10.00% (33.3% x 30%)
        "default_val": 900_000,
    },
    {
        "key": "i_cover_call",
        "account": "IRP",
        "name": "KODEX 200타겟위클리커버드콜",
        "target_weight": 0.1333,  # 13.33% (33.3% x 40%)
        "default_val": 1_200_000,
    },
    {
        "key": "i_bond",
        "account": "IRP",
        "name": "KODEX 단기채권PLUS",
        "target_weight": 0.1000,  # 10.00% (33.3% x 30%)
        "default_val": 900_000,
    },
]


def money(value):
    return f"{int(value):,}원"


def show_rebalancing_dashboard(user_id=None, cookies=None):
    st.title("⚖️ 포트폴리오 리밸런싱 & 자산 관리")
    st.caption("목표 비중 이탈률을 감지하고, 절세 및 수수료 절감을 위한 **매수 전용(Buy-Only) 리밸런싱 플랜**을 제공합니다.")

    st.divider()

    # =========================================================
    # 0. DB 데이터 조회 및 현재 월 기준 납입금/평가액 연동
    # =========================================================
    now = datetime.datetime.now()
    current_year = str(now.year)
    current_month_idx = now.month - 1  # 0 ~ 11 인덱스

    db_this_month_contribution = 0
    portfolio_initial_data = []

    # DB에서 사용자의 납입 계획 조회
    user_plan = get_user_plan(user_id) if user_id else {}
    year_plan = user_plan.get(current_year, {}).get("monthly_data", {})

    # 전체 DB에 입력된 총 누적 납입금 확인
    total_db_accumulated = sum(
        sum(year_plan.get(item["key"], [0] * 12)[: current_month_idx + 1])
        for item in ETF_CONFIG
    )

    for item in ETF_CONFIG:
        db_key = item["key"]
        monthly_list = year_plan.get(db_key, [0] * 12)

        # 이번 달 신규 납입 예정금액 추출
        this_month_val = monthly_list[current_month_idx] if len(monthly_list) > current_month_idx else 0
        db_this_month_contribution += this_month_val

        # 과거~현재까지의 누적 납입금
        accumulated_val = sum(monthly_list[: current_month_idx + 1])

        # DB에 기록된 내역이 전혀 없을 때만 기본 세팅값(default_val) 적용
        initial_val = accumulated_val if total_db_accumulated > 0 else item["default_val"]

        portfolio_initial_data.append({
            "account": item["account"],
            "name": item["name"],
            "current_val": initial_val,
            "target_weight": item["target_weight"],
        })

    # 기본값 설정 (DB 납입금이 없으면 75만 원 기본 적용)
    default_contribution = db_this_month_contribution if db_this_month_contribution > 0 else 750_000

    # =========================================================
    # 1. 설정 및 입력 섹션
    # =========================================================
    st.subheader("⚙️ 이번 달 리밸런싱 조건 설정")
    c1, c2 = st.columns(2)

    with c1:
        new_contribution = st.number_input(
            f"💵 이번 달({now.month}월) 신규 추가 납입금 (원)",
            min_value=0,
            value=default_contribution,
            step=50_000,
            format="%d",
            help="DB 납입 플랜 기반으로 자동 계산된 이번 달 계획 금액입니다.",
        )

    with c2:
        threshold_pct = st.slider(
            "⚠️ 비중 이탈 허용 임계치 (Threshold %)",
            min_value=1.0,
            max_value=10.0,
            value=5.0,
            step=0.5,
            help="목표 비중 대비 설정한 % 이상 이탈할 경우 알림 및 리밸런싱을 권장합니다.",
        )
    threshold = threshold_pct / 100.0

    st.divider()

    # =========================================================
    # 2. 현재 자산 입력 (st.data_editor)
    # =========================================================
    st.subheader("📂 보유 포트폴리오 현황")
    st.caption("현재 보유 중인 계좌별 ETF 평가금액을 수정하면 실시간으로 비중 계산이 업데이트됩니다.")

    df_input = pd.DataFrame(portfolio_initial_data)
    df_input["target_weight_pct"] = df_input["target_weight"] * 100

    edited_df = st.data_editor(
        df_input,
        key="rebalance_portfolio_editor",
        hide_index=True,
        column_config={
            "account": st.column_config.TextColumn("계좌", disabled=True, width="small"),
            "name": st.column_config.TextColumn("ETF 종목명", disabled=True, width="medium"),
            "current_val": st.column_config.NumberColumn("현재 평가금액", format="%,d원", min_value=0, step=10000),
            "target_weight_pct": st.column_config.NumberColumn("목표 비중(%)", format="%.1f%%", disabled=True,
                                                               width="small"),
        },
        column_order=["account", "name", "target_weight_pct", "current_val"],
        use_container_width=True,
    )

    # 데이터 구조 재변환
    portfolio_items = []
    for _, row in edited_df.iterrows():
        portfolio_items.append({
            "account": row["account"],
            "name": row["name"],
            "current_val": int(row["current_val"]),
            "target_weight": float(row["target_weight_pct"]) / 100.0,
        })

    # =========================================================
    # 3. 리밸런싱 연산 및 결과 출력
    # =========================================================
    result = calculate_buy_only_rebalancing(
        portfolio_items=portfolio_items,
        new_contribution=new_contribution,
        threshold=threshold,
    )

    # 이탈 임계치(threshold)를 초과한 종목 목록 추출
    drifted_items = [
        f"**{p['name']}** ({'+' if p['drift'] > 0 else ''}{p['drift'] * 100:.1f}%p)"
        for p in result["buy_plans"]
        if abs(p["drift"]) >= threshold
    ]

    # KPI 시각화
    st.subheader("🎯 포트폴리오 진단 및 KPI")
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric("현재 총 자산", money(result["total_current"]))
    with m2:
        st.metric("신규 매수 자금", money(result["new_contribution"]))
    with m3:
        st.metric("최대 비중 이탈률", f"{result['max_drift'] * 100:.1f}%p")
    with m4:
        if result["rebalance_needed"]:
            st.metric("리밸런싱 상태", "⚠️ 조정 필요", delta=f"{threshold_pct}% 초과", delta_color="inverse")
        else:
            st.metric("리밸런싱 상태", "✅ 정상 유지", delta="비중 안정적")

    if result["rebalance_needed"]:
        drifted_str = ", ".join(drifted_items)
        st.warning(
            f"⚠️ **목표 비중 이탈 종목:** {drifted_str}\n\n"
            f"위 종목이 목표 대비 **{threshold_pct}%p 이상 이탈**했습니다. "
            f"기존 자산 매도 없이, 아래 추천된 **매수 전용 가이드**대로 신규 자금을 배분하여 비중을 맞춰보세요."
        )

    # =========================================================
    # 4. 차트 분석 (현재 비중 vs 목표 비중)
    # =========================================================
    st.write("")
    chart_data = []
    for item in result["buy_plans"]:
        chart_data.append({
            "종목명": item["name"],
            "구분": "현재 비중",
            "비중(%)": round(item["current_weight"] * 100, 1),
        })
        chart_data.append({
            "종목명": item["name"],
            "구분": "목표 비중",
            "비중(%)": round(item["target_weight"] * 100, 1),
        })

    df_chart = pd.DataFrame(chart_data)
    fig = px.bar(
        df_chart,
        x="종목명",
        y="비중(%)",
        color="구분",
        barmode="group",
        title="📊 현재 비중 vs 목표 비중 비교",
        text_auto=True,
    )
    fig.update_layout(xaxis_title="", yaxis_title="비중 (%)", height=380)
    st.plotly_chart(fig, use_container_width=True)

    # =========================================================
    # 5. 매수 전용 리밸런싱 추천 테이블
    # =========================================================
    st.subheader("💡 이번 달 추천 ETF 매수 가이드")

    plan_rows = []
    for p in result["buy_plans"]:
        drift_val = p["drift"] * 100
        drift_str = f"+{drift_val:.1f}%p" if drift_val > 0 else f"{drift_val:.1f}%p"

        plan_rows.append({
            "계좌": p["account"],
            "ETF 종목명": p["name"],
            "현재 비중": f"{p['current_weight'] * 100:.1f}%",
            "목표 비중": f"{p['target_weight'] * 100:.1f}%",
            "괴리율": drift_str,
            "추천 매수 금액": money(p["recommended_buy"]),
        })

    df_plan = pd.DataFrame(plan_rows)
    st.dataframe(df_plan, use_container_width=True, hide_index=True)

    st.info(
        "💡 **알아두기:** 추천 매수 금액은 10,000원 단위로 자동 절사 조정되어 산출됩니다."
    )