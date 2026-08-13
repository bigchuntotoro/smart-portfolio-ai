import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from src.core.portfolio import calculate_buy_only_rebalancing
from src.db.contribution_dao import get_user_plan

# =========================================================
# 1. 8월~12월(5개월) 총 목표 예산 및 9월 이후 월 납입금 설정
# =========================================================
TOTAL_TARGET_BUDGET = 9_000_000  # 총 목표 금액: 900만 원
TOTAL_MONTHS = 5                  # 8월 ~ 12월 (5개월)

# 8월 실제 납입분 반영 후 남은 4개월(9월~12월) 계좌별 월 납입 목표액
# - 연금저축: 남은 480만 원 / 4개월 = 월 1,200,000원
# - IRP: 남은 1,705,000원(300만 - 8월 129.5만) / 4개월 = 월 426,250원
MONTHLY_PENSION_TARGET = 1_200_000
MONTHLY_IRP_TARGET = 426_250  # 8월 미달성분(2.5만 원) 반영

MONTHLY_TOTAL_CONTRIBUTION = MONTHLY_PENSION_TARGET + MONTHLY_IRP_TARGET  # 총 월 1,626,250원

# 9월 신규 납입금 계좌별 배분 비율 (1,200,000원 : 426,250원)
ACCOUNT_MONTHLY_WEIGHTS = {
    "연금저축": MONTHLY_PENSION_TARGET / MONTHLY_TOTAL_CONTRIBUTION,  # 약 73.79%
    "IRP": MONTHLY_IRP_TARGET / MONTHLY_TOTAL_CONTRIBUTION,            # 약 26.21%
}

# 계좌별 총 목표 비중 (전체 900만 원 기준)
ACCOUNT_TARGET_WEIGHTS = {
    "연금저축": 600 / 900,  # 66.67%
    "IRP": 300 / 900,       # 33.33%
}

# =========================================================
# 2. 계좌 내 ETF 목표 비중 및 8월 납입 기준 초기값 설정
# =========================================================
ETF_CONFIG = [
    # 연금저축 계좌 (월 120만 원 / 5개월 총 600만 원)
    {
        "key": "p_sp500",
        "account": "연금저축",
        "name": "TIGER 미국S&P500",
        "weight_in_account": 0.25,  # 25%
        "default_val": 300_000,     # 8월 납입 완료금액
    },
    {
        "key": "p_nasdaq",
        "account": "연금저축",
        "name": "KODEX 미국나스닥100",
        "weight_in_account": 0.25,  # 25%
        "default_val": 300_000,
    },
    {
        "key": "p_dividend",
        "account": "연금저축",
        "name": "KODEX 미국배당다우존스",
        "weight_in_account": 0.50,  # 50%
        "default_val": 600_000,
    },
    # IRP 계좌 (8월 단기채권PLUS 90만 원 완납 + 주식형 39.5만 원 실제 납입 반영)
    {
        "key": "i_high_div",
        "account": "IRP",
        "name": "KODEX 주주환원고배당주",
        "weight_in_account": 0.30,  # 30%
        "default_val": 180_000,     # 8월 실제 납입액
    },
    {
        "key": "i_cover_call",
        "account": "IRP",
        "name": "KODEX 200타겟위클리커버드콜",
        "weight_in_account": 0.40,  # 40%
        "default_val": 215_000,     # 8월 실제 납입액
    },
    {
        "key": "i_bond",
        "account": "IRP",
        "name": "KODEX 단기채권PLUS",
        "weight_in_account": 0.30,  # 30%
        "default_val": 900_000,     # 8월 90만 원 완납 반영
    },
]


def money(value):
    return f"{int(value):,}원"


def show_rebalancing_dashboard(user_id=None, cookies=None):
    st.title("⚖️ 계좌별 독립 포트폴리오 리밸런싱 & 자산 관리")
    st.caption("연금저축과 IRP 계좌를 분리하여 **계좌별 매수 전용(Buy-Only) 리밸런싱 플랜**을 제공합니다.")

    st.divider()

    # =========================================================
    # 0. DB 데이터 조회 및 초기값 산출
    # =========================================================
    now = datetime.datetime.now()
    current_year = str(now.year)
    current_month_idx = now.month - 1  # 0 ~ 11 인덱스

    db_this_month_contribution = 0
    portfolio_initial_data = []

    user_plan = get_user_plan(user_id) if user_id else {}
    year_plan = user_plan.get(current_year, {}).get("monthly_data", {})

    total_db_accumulated = sum(
        sum(year_plan.get(item["key"], [0] * 12)[: current_month_idx + 1])
        for item in ETF_CONFIG
    )

    for item in ETF_CONFIG:
        db_key = item["key"]
        account_name = item["account"]
        monthly_list = year_plan.get(db_key, [0] * 12)

        this_month_val = monthly_list[current_month_idx] if len(monthly_list) > current_month_idx else 0
        db_this_month_contribution += this_month_val

        accumulated_val = sum(monthly_list[: current_month_idx + 1])
        initial_val = accumulated_val if total_db_accumulated > 0 else item["default_val"]

        # 5개월 총 목표 금액 중 해당 종목 목표액 계산
        account_total_target = TOTAL_TARGET_BUDGET * ACCOUNT_TARGET_WEIGHTS[account_name]
        item_total_target = account_total_target * item["weight_in_account"]
        item_august_target = item_total_target / TOTAL_MONTHS  # 8월 목표금액

        portfolio_initial_data.append({
            "account": account_name,
            "name": item["name"],
            "current_val": initial_val,
            "weight_in_account": item["weight_in_account"],
            "august_target_val": item_august_target,
            "total_target_val": item_total_target,
        })

    # 메타 정보 매핑 사전 생성 (목표 금액 관련 정보 보존)
    meta_map = {
        item["name"]: {
            "august_target_val": item["august_target_val"],
            "total_target_val": item["total_target_val"],
            "current_val": item["current_val"],
        }
        for item in portfolio_initial_data
    }

    # =========================================================
    # 1. 설정 및 입력 섹션 (다음 달 = 9월 매수 계획)
    # =========================================================
    st.subheader("⚙️ 9월 신규 납입 및 조건 설정")
    c1, c2 = st.columns(2)

    with c1:
        new_contribution = st.number_input(
            "💵 다음 달(9월) 총 신규 추가 납입금 (원)",
            min_value=0,
            value=MONTHLY_TOTAL_CONTRIBUTION,  # 1,626,250원
            step=10_000,
            format="%d",
            help="8월 납입분 반영 후 12월 목표 달성을 위해 9월에 추가할 금액입니다. (연금저축 120만 + IRP 42.6만 원)",
        )

    with c2:
        threshold_pct = st.slider(
            "⚠️ 비중 이탈 허용 임계치 (Threshold %)",
            min_value=1.0,
            max_value=10.0,
            value=5.0,
            step=0.5,
            help="계좌 내 목표 비중 대비 설정한 % 이상 이탈할 경우 리밸런싱을 권장합니다.",
        )
    threshold = threshold_pct / 100.0

    st.divider()

    # =========================================================
    # 2. 보유 포트폴리오 현황 (8월 납입 후 평가금액)
    # =========================================================
    st.subheader("📂 현재 보유 포트폴리오 현황 (8월 납입 반영)")
    st.caption("현재 보유 중인 ETF 평가금액을 수정하면 계좌별 9월 추천 매수 금액이 업데이트됩니다.")

    df_input = pd.DataFrame(portfolio_initial_data)
    df_input["target_weight_pct"] = df_input["weight_in_account"] * 100

    edited_df = st.data_editor(
        df_input,
        key="rebalance_portfolio_editor",
        hide_index=True,
        column_config={
            "account": st.column_config.TextColumn("계좌", disabled=True, width="small"),
            "name": st.column_config.TextColumn("ETF 종목명", disabled=True, width="medium"),
            "target_weight_pct": st.column_config.NumberColumn("계좌 내 목표 비중(%)", format="%.1f%%", disabled=True, width="small"),
            "current_val": st.column_config.NumberColumn("현재 평가금액 (8월 반영)", format="%,d원", min_value=0, step=10000),
        },
        column_order=["account", "name", "target_weight_pct", "current_val"],
        use_container_width=True,
    )

    # 계좌별 분리 입력을 위한 딕셔너리 구성
    account_portfolio_items = {}

    for _, row in edited_df.iterrows():
        account_name = row["account"]
        weight_in_account = float(row["target_weight_pct"]) / 100.0
        current_val = int(row["current_val"])
        name = row["name"]

        if account_name not in account_portfolio_items:
            account_portfolio_items[account_name] = []

        account_portfolio_items[account_name].append({
            "account": account_name,
            "name": name,
            "current_val": current_val,
            "target_weight": weight_in_account,  # 계좌 내 비중
        })

        if name in meta_map:
            meta_map[name]["current_val"] = current_val

    # =========================================================
    # 3. 계좌별 독립 리밸런싱 연산
    # =========================================================
    account_results = {}
    combined_buy_plans = []

    for acc_name, items in account_portfolio_items.items():
        # 조정된 9월 납입금 비율로 계좌별 신규 납입금 배분
        acc_weight = ACCOUNT_MONTHLY_WEIGHTS.get(acc_name, 0.0)
        acc_new_contribution = int(new_contribution * acc_weight)

        res = calculate_buy_only_rebalancing(
            portfolio_items=items,
            new_contribution=acc_new_contribution,
            threshold=threshold,
        )
        account_results[acc_name] = res
        combined_buy_plans.extend(res["buy_plans"])

    # =========================================================
    # 4. 계좌별 진단 및 KPI
    # =========================================================
    st.subheader("🎯 계좌별 포트폴리오 진단 및 KPI")

    for acc_name, res in account_results.items():
        st.markdown(f"#### 📌 {acc_name} 계좌")
        m1, m2, m3, m4 = st.columns(4)

        with m1:
            st.metric("현재 자산 (8월)", money(res["total_current"]))
        with m2:
            st.metric("9월 매수 예정액", money(res["new_contribution"]))
        with m3:
            st.metric("최대 비중 이탈률", f"{res['max_drift'] * 100:.1f}%p")
        with m4:
            if res["rebalance_needed"]:
                st.metric("리밸런싱 상태", "⚠️ 조정 필요", delta=f"{threshold_pct}% 초과", delta_color="inverse")
            else:
                st.metric("리밸런싱 상태", "✅ 정상 유지", delta="비중 안정적")

    st.divider()

    # =========================================================
    # 5. 차트 분석 (계좌 내 현재 비중 vs 계좌 내 목표 비중)
    # =========================================================
    st.subheader("📊 계좌별 비중 비교 (현재 비중 vs 계좌 내 목표 비중)")

    chart_data = []
    for item in combined_buy_plans:
        chart_data.append({
            "계좌": item["account"],
            "종목명": item["name"],
            "구분": "현재 비중",
            "비중(%)": round(item["current_weight"] * 100, 1),
        })
        chart_data.append({
            "계좌": item["account"],
            "종목명": item["name"],
            "구분": "계좌 내 목표 비중",
            "비중(%)": round(item["target_weight"] * 100, 1),
        })

    df_chart = pd.DataFrame(chart_data)

    fig = px.bar(
        df_chart,
        x="종목명",
        y="비중(%)",
        color="구분",
        facet_col="계좌",
        barmode="group",
        text_auto=True,
    )
    fig.update_layout(height=400)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    st.plotly_chart(fig, use_container_width=True)

    # =========================================================
    # 6. 다음 달(9월) 추천 ETF 매수 가이드 (계좌별 분리 & 합계)
    # =========================================================
    st.subheader("💡 다음 달(9월) 추천 ETF 매수 가이드")

    target_accounts = ["연금저축", "IRP"]
    account_subtotals = {}
    grand_total_buy = 0

    for acc_name in target_accounts:
        acc_plans = [p for p in combined_buy_plans if p["account"] == acc_name]
        if not acc_plans:
            continue

        st.markdown(f"#### 🏦 {acc_name} 매수 가이드")

        plan_rows = []
        subtotal = 0

        for p in acc_plans:
            name = p["name"]
            meta = meta_map.get(name, {})

            curr_val = meta.get("current_val", 0)
            aug_target = meta.get("august_target_val", 0)
            total_target = meta.get("total_target_val", 0)

            monthly_achievement = (curr_val / aug_target * 100) if aug_target > 0 else 0
            total_achievement = (curr_val / total_target * 100) if total_target > 0 else 0

            recommended_buy = p["recommended_buy"]
            subtotal += recommended_buy

            plan_rows.append({
                "ETF 종목명": name,
                "월 정해진 비율 달성률": f"{monthly_achievement:.1f}%",
                "통합 목표 달성률 (전체 900만)": f"{total_achievement:.1f}%",
                "9월 추천 매수 금액": money(recommended_buy),
            })

        account_subtotals[acc_name] = subtotal
        grand_total_buy += subtotal

        df_acc_plan = pd.DataFrame(plan_rows)
        st.dataframe(df_acc_plan, use_container_width=True, hide_index=True)

        # 계좌별 소계 카드
        st.markdown(f"👉 **{acc_name} 추천 매수 소계:** `{money(subtotal)}`")
        st.write("")

    # =========================================================
    # 7. 🔥 [신규 추가] 8월 vs 9월 매수 금액 직접 비교
    # =========================================================
    st.divider()
    st.subheader("🔄 8월 vs 9월 매수 금액 비교")
    st.caption("8월 실제 납입 금액과 9월 추천 매수 금액을 종목별/계좌별로 비교합니다.")

    compare_rows = []
    chart_compare_data = []

    august_total_sum = 0
    september_total_sum = 0

    for item in combined_buy_plans:
        acc = item["account"]
        name = item["name"]
        aug_val = meta_map.get(name, {}).get("current_val", 0)
        sep_val = item["recommended_buy"]
        diff_val = sep_val - aug_val

        august_total_sum += aug_val
        september_total_sum += sep_val

        # 비교 표용 데이터
        compare_rows.append({
            "계좌": acc,
            "ETF 종목명": name,
            "8월 실제 매수액": money(aug_val),
            "9월 추천 매수액": money(sep_val),
            "증감액": f"{'+' if diff_val > 0 else ''}{int(diff_val):,}원",
        })

        # 비교 차트용 데이터 (Long Format)
        chart_compare_data.append({"계좌": acc, "종목명": name, "월": "8월 실제", "매수금액(원)": aug_val})
        chart_compare_data.append({"계좌": acc, "종목명": name, "월": "9월 추천", "매수금액(원)": sep_val})

    # 비교 테이블 출력
    df_compare = pd.DataFrame(compare_rows)
    st.dataframe(df_compare, use_container_width=True, hide_index=True)

    # 종목별 8월 vs 9월 매수 금액 시각화 차트
    df_chart_compare = pd.DataFrame(chart_compare_data)
    fig_comp = px.bar(
        df_chart_compare,
        x="종목명",
        y="매수금액(원)",
        color="월",
        facet_col="계좌",
        barmode="group",
        text_auto=",d",
        title="📊 종목별 8월 vs 9월 매수 금액 비교 차트",
    )
    fig_comp.update_layout(height=420)
    fig_comp.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    st.plotly_chart(fig_comp, use_container_width=True)

    # 계좌별 요약 비교 카드
    st.markdown("#### 📌 계좌별 8월 vs 9월 총 매수액 요약")
    col_c1, col_c2, col_c3 = st.columns(3)

    pension_aug = sum(meta_map.get(p["name"], {}).get("current_val", 0) for p in combined_buy_plans if p["account"] == "연금저축")
    pension_sep = account_subtotals.get("연금저축", 0)

    irp_aug = sum(meta_map.get(p["name"], {}).get("current_val", 0) for p in combined_buy_plans if p["account"] == "IRP")
    irp_sep = account_subtotals.get("IRP", 0)

    with col_c1:
        st.metric(
            "연금저축 총 매수액",
            f"9월: {money(pension_sep)}",
            delta=f"8월: {money(pension_aug)} 대비 {pension_sep - pension_aug:+,d}원",
        )
    with col_c2:
        st.metric(
            "IRP 총 매수액",
            f"9월: {money(irp_sep)}",
            delta=f"8월: {money(irp_aug)} 대비 {irp_sep - irp_aug:+,d}원",
            delta_color="normal",
        )
    with col_c3:
        st.metric(
            "🔥 전체 총 매수액",
            f"9월: {money(grand_total_buy)}",
            delta=f"8월: {money(august_total_sum)} 대비 {grand_total_buy - august_total_sum:+,d}원",
        )

    st.info(
        "💡 **8월 vs 9월 매수 비교 포인트:**\n"
        "- **KODEX 단기채권PLUS**: 8월에 90만 원을 완납하여 9월 매수액은 **0원(-90만 원)**으로 감소합니다.\n"
        "- **IRP 주식형 ETF (고배당주/커버드콜)**: 8월 미달성분(2.5만 원)이 추가 반영되어 9월 매수액이 8월(39.5만 원) 대비 **약 42.6만 원(+3.1만 원)**으로 증가합니다.\n"
        "- **연금저축**: 8월과 동일하게 월 120만 원 납입을 유지합니다."
    )