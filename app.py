import streamlit as st
import os
import pandas as pd
import plotly.express as px

from dotenv import load_dotenv

# ✅ 환경변수 로드

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    st.warning("❌ OPENAI_API_KEY 없음 (.env 확인 필요)")

from src.core.portfolio import analyze_portfolio
from src.core.recommender import recommend
from src.utils.simulator import simulate
from src.ai.advisor import get_advice

st.set_page_config(page_title="자산 관리 AI", layout="wide")

st.title("💰 Smart Portfolio AI")

# ------------------------

# 입력

# ------------------------

age = st.number_input("나이", value=54)
cash = st.number_input("현금", value=280000000)
monthly = st.number_input("월 저축", value=3000000)
etf_amount = st.number_input("ETF 금액", value=80000000)

data = {
"age": age,
"cash": cash,
"products": [
{"type": "ETF", "amount": etf_amount}
]
}

# ------------------------

# 실행

# ------------------------

if st.button("분석하기"):

    result = analyze_portfolio(data)
    rec = recommend(data)

    st.subheader("📊 포트폴리오 분석")
    st.write(result)

    st.subheader("📌 추천 투자")
    st.write(rec)

    # ------------------------
    # 📈 미래 자산 (라인 그래프)
    # ------------------------
    st.subheader("📈 미래 자산 성장")

    years = list(range(1, 11))
    values = [simulate(i, monthly, 0.05) for i in years]

    df_growth = pd.DataFrame({
        "연도": years,
        "자산": values
    })

    fig_line = px.line(
        df_growth,
        x="연도",
        y="자산",
        markers=True,
        title="10년 자산 성장 시뮬레이션"
    )

    fig_line.update_layout(
        xaxis_title="연도",
        yaxis_title="자산 (원)"
    )

    st.plotly_chart(fig_line, use_container_width=True)

    # ------------------------
    # 📊 자산 비율 (도넛 차트)
    # ------------------------
    st.subheader("📊 자산 비율")

    df_pie = pd.DataFrame({
        "자산": ["현금", "ETF"],
        "금액": [cash, etf_amount]
    })

    fig_pie = px.pie(
        df_pie,
        names="자산",
        values="금액",
        hole=0.4  # 도넛 스타일
    )

    fig_pie.update_traces(
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>금액: %{value:,}원<br>비율: %{percent}"
    )

    st.plotly_chart(fig_pie, use_container_width=True)

    # ------------------------
    # 🤖 AI 설명
    # ------------------------
    st.subheader("🤖 AI 조언")

    if not os.getenv("OPENAI_API_KEY"):
        st.warning("API 키 필요")
    else:
        try:
            advice = get_advice(result)
            st.write(advice)
        except Exception as e:
            st.error(f"AI 오류: {e}")

