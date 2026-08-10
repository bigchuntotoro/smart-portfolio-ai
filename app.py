import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.api.etf_api import ETFData
from src.core.portfolio import analyze_portfolio
from src.core.recommender import recommend
from src.utils.simulator import simulate

# ========================================
# 1. 페이지 설정 & Custom CSS
# ========================================
load_dotenv()

st.set_page_config(
    page_title="Smart Portfolio AI PRO",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 고급스러운 대시보드 스타일 CSS
st.markdown("""
<style>
    /* 기본 배경 및 폰트 설정 */
    .stApp {
        background-color: #0e1117;
    }

    /* 지표(Metric) 카드 스타일링 */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #90a4ae !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #4fc3f7 !important;
    }

    /* 컨테이너 카드 스타일 */
    .css-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
    }

    /* 버튼 디자인 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# 2. 세션 및 인증 처리
# ========================================
if "login_user" not in st.session_state:
    st.session_state.login_user = None

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# 사이드바 상단 사용자 정보
if st.session_state.login_user:
    st.sidebar.markdown(f"### 👤 안녕하세요, **{st.session_state.login_user}**님")
    if st.sidebar.button("🚪 로그아웃", key="logout_btn"):
        st.session_state.login_user = None
        st.rerun()
    st.sidebar.divider()

st.title("💰 Smart Portfolio AI PRO")

if st.session_state.login_user is None:
    menu = ["로그인", "회원가입"]
    choice = st.sidebar.selectbox("🔑 접속 메뉴", menu)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='css-card'>", unsafe_allow_html=True)
        if choice == "로그인":
            st.subheader("🔑 로그인")
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")

            if st.button("로그인", type="primary"):
                cursor.execute(
                    "SELECT * FROM users WHERE username=? AND password=?",
                    (username, password)
                )
                user = cursor.fetchone()
                if user:
                    st.session_state.login_user = username
                    st.success(f"{username}님 환영합니다!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호 오류입니다.")

        elif choice == "회원가입":
            st.subheader("📝 회원가입")
            new_user = st.text_input("아이디 생성")
            new_pass = st.text_input("비밀번호 생성", type="password")

            if st.button("회원가입 완료"):
                try:
                    cursor.execute(
                        "INSERT INTO users (username, password) VALUES (?, ?)",
                        (new_user, new_pass)
                    )
                    conn.commit()
                    st.success("회원가입 성공! 로그인해 주세요.")
                except Exception:
                    st.error("이미 존재하는 아이디입니다.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ========================================
# 3. 사이드바 입력 영역
# ========================================
def money_input(label, default):
    if label not in st.session_state:
        st.session_state[label] = f"{default:,}"

    raw = st.sidebar.text_input(label, st.session_state[label])
    try:
        value = int(raw.replace(",", ""))
        st.session_state[label] = f"{value:,}"
    except ValueError:
        value = default
        st.sidebar.warning(f"⚠️ {label}: 숫자만 입력 가능합니다.")
    return value


st.sidebar.header("⚙️ 포트폴리오 설정")

age = st.sidebar.number_input("나이 (세)", value=54, step=1)
st.sidebar.subheader("💵 보유 자산")
cash = money_input("현금", 280000000)
etf_amount = money_input("현재 ETF 금액", 80000000)
bond_amount = money_input("현재 채권 금액", 50000000)
pension_amount = money_input("현재 연금 금액", 30000000)

st.sidebar.subheader("📅 월 적립식 투자")
monthly_etf = money_input("ETF 월 투자", 1500000)
monthly_bond = money_input("채권 월 투자", 1000000)
monthly_pension = money_input("연금 월 투자", 500000)

# ETF 데이터 패치
try:
    etf_api = ETFData()
    etfs = etf_api.get_etfs()
except Exception as e:
    st.error(f"ETF 데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

if not etfs:
    st.error("ETF 데이터를 불러올 수 없습니다.")
    st.stop()

st.sidebar.subheader("🎯 Target ETF 선택")
selected_etf = st.sidebar.selectbox(
    "관심 ETF",
    etfs,
    format_func=lambda x: x.get("name", "Unknown ETF")
)

selected_etf = selected_etf or {}
etf_name = selected_etf.get("name", "Unknown ETF")
etf_return = float(selected_etf.get("return_1y", 5.0))
etf_risk = int(selected_etf.get("risk", 3))

# ========================================
# 4. 상단 요약 KPI 섹션
# ========================================
total_asset = cash + etf_amount + bond_amount + pension_amount
monthly_total = monthly_etf + monthly_bond + monthly_pension

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("총 자산", f"{total_asset:,} 원")
kpi2.metric("월 총 투자액", f"{monthly_total:,} 원")
kpi3.metric("선택 ETF", etf_name)
kpi4.metric("연령 / 위험도", f"{age}세 / Risk {etf_risk}")

st.write("")

# ========================================
# 5. 메인 탭 화면 구성
# ========================================
tab1, tab2, tab3 = st.tabs(["📊 자산 현황", "🤖 AI 분석 & 리스크", "📈 10년 성과 시뮬레이션"])

# --- TAB 1: 자산 구성 현황 ---
with tab1:
    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("🍩 자산 비중 분포")
        df_pie = pd.DataFrame({
            "자산": ["현금", "ETF", "채권", "연금"],
            "금액": [cash, etf_amount, bond_amount, pension_amount]
        })
        fig_pie = px.pie(
            df_pie,
            names="자산",
            values="금액",
            hole=0.55,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("📋 자산 세부 내역")
        df_summary = pd.DataFrame({
            "자산 항목": ["현금", f"ETF ({etf_name})", "채권 (국공채)", "연금 (IRP/연금저축)"],
            "현재 보유 금액": [f"{cash:,}원", f"{etf_amount:,}원", f"{bond_amount:,}원", f"{pension_amount:,}원"],
            "월 적립금": ["-", f"{monthly_etf:,}원", f"{monthly_bond:,}원", f"{monthly_pension:,}원"],
            "기대 수익률": ["-", f"{etf_return}%", "3.0%", "5.0%"]
        })
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

# --- TAB 2: AI 분석 & 리스크 분석 ---
with tab2:
    col_ai, col_risk = st.columns([1.2, 0.8])

    data = {
        "age": age,
        "cash": cash,
        "products": [
            {"type": "ETF", "name": etf_name, "amount": etf_amount, "return": etf_return, "risk": etf_risk},
            {"type": "채권", "name": "국공채", "amount": bond_amount, "return": 3.0, "risk": 1},
            {"type": "연금", "name": "IRP/연금저축", "amount": pension_amount, "return": 5.0, "risk": 2},
        ],
    }

    with col_ai:
        st.subheader("🤖 AI 진단 및 리포트")
        if st.button("🚀 AI 진단 실행하기", type="primary"):
            with st.spinner("포트폴리오 분석 중..."):
                try:
                    result = analyze_portfolio(data)
                    rec = recommend(data)

                    st.success("✔ 진단 완료")
                    st.markdown("#### 📊 분석 지표")
                    st.json(result)

                    st.markdown("#### 📌 추천 전략")
                    st.info(rec)
                except Exception as e:
                    st.error(f"오류 발생: {e}")
        else:
            st.caption("버튼을 누르면 AI가 현재 포트폴리오의 진단 결과를 생성합니다.")

    with col_risk:
        st.subheader("⚠️ 리스크 레벨 측정")
        total_invested = etf_amount + bond_amount + pension_amount
        risk_score = 0 if total_invested == 0 else (
                                                               etf_amount * etf_risk + bond_amount * 1 + pension_amount * 2) / total_invested

        if risk_score > 4:
            status_text, status_color = "공격투자형 🚨", "#ff5252"
        elif risk_score > 2:
            status_text, status_color = "위험중립형 ⚖️", "#ffb74d"
        else:
            status_text, status_color = "안정지향형 ✅", "#66bb6a"

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=round(risk_score, 2),
            title={'text': f"성향: {status_text}", 'font': {'size': 16}},
            gauge={
                'axis': {'range': [0, 5]},
                'bar': {'color': status_color},
                'steps': [
                    {'range': [0, 2], 'color': "rgba(102, 187, 106, 0.2)"},
                    {'range': [2, 4], 'color': "rgba(255, 183, 77, 0.2)"},
                    {'range': [4, 5], 'color': "rgba(255, 82, 82, 0.2)"},
                ],
            }
        ))
        fig_gauge.update_layout(
            height=280,
            margin=dict(t=40, b=10, l=30, r=30),
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

# --- TAB 3: 시뮬레이션 ---
with tab3:
    st.subheader("📈 복리 기반 10년 자산 성장 추이")

    etf_r = etf_return / 100
    bond_r = 0.03
    pension_r = 0.05
    years = list(range(1, 11))
    values = []

    for y in years:
        etf_val = simulate(y, monthly_etf, etf_r)
        bond_val = simulate(y, monthly_bond, bond_r)
        pension_val = simulate(y, monthly_pension, pension_r)

        # 총 예상 자산 (초기 자산 + 연도별 누적 수익)
        total_future = total_asset + etf_val + bond_val + pension_val
        values.append(total_future)

    df_sim = pd.DataFrame({"연도": [f"{y}년후" for y in years], "예상 총 자산": values})

    fig_line = px.line(
        df_sim,
        x="연도",
        y="예상 총 자산",
        markers=True,
        text="예상 총 자산"
    )
    fig_line.update_traces(
        texttemplate='%{text:,.0f}원',
        textposition='top center',
        line_color='#4fc3f7',
        line_width=3
    )
    fig_line.update_layout(
        yaxis_tickformat=",",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=30, b=20, l=20, r=20)
    )
    st.plotly_chart(fig_line, use_container_width=True)