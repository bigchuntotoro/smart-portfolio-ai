import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from src.api.etf_api import ETFData
from src.core.portfolio import analyze_portfolio
from src.core.recommender import recommend
from src.utils.simulator import simulate


# ========================================
# 환경변수
# ========================================

load_dotenv()

st.set_page_config(
    page_title="자산 관리 AI PRO",
    layout="wide"
)

st.title("💰 Smart Portfolio AI PRO")


# ========================================
# 입력 영역
# ========================================

st.sidebar.header("📥 입력")

age = st.sidebar.number_input(
    "나이",
    value=54
)

cash = st.sidebar.number_input(
    "현금",
    value=280000000
)

monthly_etf = st.sidebar.number_input(
    "ETF 월 투자",
    value=1500000
)

monthly_bond = st.sidebar.number_input(
    "채권 월 투자",
    value=1000000
)

monthly_pension = st.sidebar.number_input(
    "연금(IRP/연금저축)",
    value=500000
)

etf_amount = st.sidebar.number_input(
    "현재 ETF 금액",
    value=80000000
)

bond_amount = st.sidebar.number_input(
    "현재 채권 금액",
    value=50000000
)

pension_amount = st.sidebar.number_input(
    "현재 연금 금액",
    value=30000000
)


# ========================================
# ETF 데이터 불러오기
# ========================================

try:
    etf_api = ETFData()
    etfs = etf_api.get_etfs()

except Exception as e:
    st.error(
        f"ETF 데이터를 불러오는 중 오류가 발생했습니다: {e}"
    )
    st.stop()


if not etfs:
    st.error("ETF 데이터를 불러올 수 없습니다.")
    st.stop()


# ========================================
# ETF 선택
# ========================================

selected_etf = st.sidebar.selectbox(
    "ETF 선택",
    etfs,
    format_func=lambda x: x.get(
        "name",
        "Unknown ETF"
    )
)


# ========================================
# 선택 ETF 안전 보정
# ========================================

selected_etf = selected_etf or {}

etf_name = selected_etf.get(
    "name",
    "Unknown ETF"
)

etf_return = float(
    selected_etf.get(
        "return_1y",
        5.0
    )
)

etf_risk = int(
    selected_etf.get(
        "risk",
        3
    )
)


# ========================================
# 선택 ETF 표시
# ========================================

st.write("### 📌 선택 ETF")

st.write(
    {
        "name": etf_name,
        "return_1y": etf_return,
        "risk": etf_risk,
    }
)


# ========================================
# 포트폴리오 데이터 구성
# ========================================

data = {
    "age": age,
    "cash": cash,
    "products": [
        {
            "type": "ETF",
            "name": etf_name,
            "amount": etf_amount,
            "return": etf_return,
            "risk": etf_risk,
        },
        {
            "type": "채권",
            "name": "국공채",
            "amount": bond_amount,
            "return": 3.0,
            "risk": 1,
        },
        {
            "type": "연금",
            "name": "IRP/연금저축",
            "amount": pension_amount,
            "return": 5.0,
            "risk": 2,
        },
    ],
}


# ========================================
# 포트폴리오 분석
# ========================================

if st.button("🚀 분석 시작"):

    try:
        result = analyze_portfolio(data)
        rec = recommend(data)

        st.subheader("📊 포트폴리오 분석")
        st.write(result)

        st.subheader("📌 추천 전략")
        st.write(rec)

    except Exception as e:
        st.error(
            f"분석 중 오류 발생: {e}"
        )


# ========================================
# 자산 성장
# ========================================

st.subheader("📈 10년 자산 성장")

etf_r = etf_return / 100
bond_r = 0.03
pension_r = 0.05

years = list(range(1, 11))
values = []

total = (
    cash
    + etf_amount
    + bond_amount
    + pension_amount
)


for y in years:

    etf_val = simulate(
        y,
        monthly_etf,
        etf_r
    )

    bond_val = simulate(
        y,
        monthly_bond,
        bond_r
    )

    pension_val = simulate(
        y,
        monthly_pension,
        pension_r
    )

    total_future = (
        total
        + etf_val
        + bond_val
        + pension_val
    )

    values.append(total_future)


df = pd.DataFrame(
    {
        "연도": years,
        "총 자산": values,
    }
)


fig = px.line(
    df,
    x="연도",
    y="총 자산",
    markers=True
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ========================================
# 자산 비율
# ========================================

st.subheader("📊 자산 비율")

df_pie = pd.DataFrame(
    {
        "자산": [
            "현금",
            "ETF",
            "채권",
            "연금",
        ],
        "금액": [
            cash,
            etf_amount,
            bond_amount,
            pension_amount,
        ],
    }
)


fig_pie = px.pie(
    df_pie,
    names="자산",
    values="금액",
    hole=0.4
)

st.plotly_chart(
    fig_pie,
    use_container_width=True
)


# ========================================
# 리스크 점수
# ========================================

st.subheader("⚠️ 포트폴리오 리스크")

total_amount = (
    etf_amount
    + bond_amount
    + pension_amount
)


if total_amount == 0:

    risk_score = 0

else:

    risk_score = (
        etf_amount * etf_risk
        + bond_amount * 1
        + pension_amount * 2
    ) / total_amount


st.metric(
    "리스크 점수",
    round(risk_score, 2)
)


if risk_score > 4:

    st.error(
        "⚠️ 공격적 포트폴리오"
    )

elif risk_score > 2:

    st.warning(
        "⚖️ 중립 포트폴리오"
    )

else:

    st.success(
        "✅ 안정형 포트폴리오"
    )
