import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.api.etf_api import ETFData
from src.core.auth import refresh_access_token
from src.core.portfolio import analyze_portfolio
from src.core.recommender import recommend
from src.db.portfolio_dao import get_portfolio, save_portfolio
from src.utils.simulator import simulate

# =========================================================
# 기본값
# =========================================================

DEFAULT_PORTFOLIO = {
    "age": 54,
    "cash": 280_000_000,
    "etf_amount": 80_000_000,
    "bond_amount": 50_000_000,
    "pension_amount": 30_000_000,
    "monthly_etf": 1_500_000,
    "monthly_bond": 1_000_000,
    "monthly_pension": 500_000,
    "selected_etf": None,
}


# =========================================================
# Refresh Token 자동 세션 복구 함수 (신규 추가)
# =========================================================

def try_auto_refresh_session(cookies):
    """
    Session State에 Access Token이 없지만 Cookie에 Refresh Token이 존재하는 경우
    Access Token을 자동 재발급받아 인증 세션을 복구합니다.
    """
    if "access_token" in st.session_state and st.session_state["access_token"]:
        return True

    # 쿠키에서 refresh_token 확인
    refresh_token = cookies.get("refresh_token")
    user_id = st.session_state.get("user_id")

    if refresh_token and user_id:
        try:
            # Refresh Token으로 새 Access Token 요청
            res = refresh_access_token(user_id, refresh_token)
            if res and res.get("access_token"):
                st.session_state["access_token"] = res["access_token"]
                return True
        except Exception as e:
            print(f"[AUTH REFRESH ERROR] {e}")

    return False


# =========================================================
# 금액 입력 함수
# =========================================================

def money_input(label, default):
    """금액을 천 단위 콤마 형식으로 입력받는다."""

    session_key = f"money_value_{label}"
    widget_key = f"money_{label}"

    if session_key not in st.session_state:
        st.session_state[session_key] = f"{default:,}"

    # text_input 초기값 설정
    raw = st.sidebar.text_input(
        label,
        value=st.session_state[session_key],
        key=widget_key,
    )

    try:
        clean_raw = raw.replace(",", "").strip()
        value = int(clean_raw)

        if value < 0:
            raise ValueError

        # 세션 값 갱신 (천단위 콤마 포맷 적용)
        formatted_val = f"{value:,}"
        st.session_state[session_key] = formatted_val

    except (ValueError, AttributeError):
        value = default
        st.session_state[session_key] = f"{default:,}"
        st.sidebar.warning(f"⚠️ {label}: 올바른 금액을 입력해주세요.")

    return value


# =========================================================
# Dashboard 위젯 상태 초기화
# =========================================================

def reset_portfolio_widget_state():
    """다른 사용자 로그인 시 이전 사용자의 Dashboard 입력값을 모두 제거한다."""

    # 특정 명시적 키 삭제
    explicit_keys = [
        "age",
        "age_input",
        "selected_etf_name",
        "selected_etf",
        "portfolio_exists",
        "ai_result",
        "ai_recommendation",
    ]

    for key in explicit_keys:
        st.session_state.pop(key, None)

    # money_ 관련 상태 및 위젯 키 일괄 삭제
    keys_to_delete = [
        k
        for k in st.session_state.keys()
        if k.startswith("money_") or k.startswith("money_value_")
    ]
    for k in keys_to_delete:
        st.session_state.pop(k, None)


# =========================================================
# DB 포트폴리오 → Session State
# =========================================================

def load_portfolio_to_session(portfolio):
    """DB에서 읽은 포트폴리오를 Session State에 저장한다."""

    st.session_state["age"] = int(portfolio["age"])
    st.session_state["money_value_현금"] = f'{portfolio["cash"]:,}'
    st.session_state["money_value_현재 ETF 금액"] = (
        f'{portfolio["etf_amount"]:,}'
    )
    st.session_state["money_value_현재 채권 금액"] = (
        f'{portfolio["bond_amount"]:,}'
    )
    st.session_state["money_value_현재 연금 금액"] = (
        f'{portfolio["pension_amount"]:,}'
    )
    st.session_state["money_value_ETF 월 투자"] = (
        f'{portfolio["monthly_etf"]:,}'
    )
    st.session_state["money_value_채권 월 투자"] = (
        f'{portfolio["monthly_bond"]:,}'
    )
    st.session_state["money_value_연금 월 투자"] = (
        f'{portfolio["monthly_pension"]:,}'
    )
    st.session_state["selected_etf_name"] = portfolio["selected_etf"]
    st.session_state["portfolio_exists"] = True


# =========================================================
# 기본 포트폴리오 → Session State
# =========================================================

def load_default_portfolio():
    """최초 가입 회원에게 기본 포트폴리오를 설정한다."""

    st.session_state["age"] = DEFAULT_PORTFOLIO["age"]
    st.session_state["money_value_현금"] = f'{DEFAULT_PORTFOLIO["cash"]:,}'
    st.session_state["money_value_현재 ETF 금액"] = (
        f'{DEFAULT_PORTFOLIO["etf_amount"]:,}'
    )
    st.session_state["money_value_현재 채권 금액"] = (
        f'{DEFAULT_PORTFOLIO["bond_amount"]:,}'
    )
    st.session_state["money_value_현재 연금 금액"] = (
        f'{DEFAULT_PORTFOLIO["pension_amount"]:,}'
    )
    st.session_state["money_value_ETF 월 투자"] = (
        f'{DEFAULT_PORTFOLIO["monthly_etf"]:,}'
    )
    st.session_state["money_value_채권 월 투자"] = (
        f'{DEFAULT_PORTFOLIO["monthly_bond"]:,}'
    )
    st.session_state["money_value_연금 월 투자"] = (
        f'{DEFAULT_PORTFOLIO["monthly_pension"]:,}'
    )
    st.session_state["selected_etf_name"] = None
    st.session_state["portfolio_exists"] = False


# =========================================================
# Dashboard
# =========================================================

def show_dashboard(user_id, cookies=None):
    # =====================================================
    # 1. 환경변수
    # =====================================================
    load_dotenv()

    # =====================================================
    # 2. 토큰 및 사용자 인증 검증 (자동 재발급 검사 추가)
    # =====================================================
    if cookies:
        try_auto_refresh_session(cookies)

    if not st.session_state.get("access_token"):
        st.error("🔒 세션이 만료되었습니다. 다시 로그인해주세요.")
        return

    if user_id is None:
        st.error("❌ 사용자 인증 정보를 확인할 수 없습니다.")
        return

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        st.error("❌ 잘못된 사용자 ID입니다.")
        return

    # =====================================================
    # 3. 로그인 사용자
    # =====================================================
    username = st.session_state.get("login_user")
    if not username:
        st.error("❌ 로그인 사용자 정보를 확인할 수 없습니다.")
        return

    # =====================================================
    # 4. CSS
    # =====================================================
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0e1117;
        }
        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 16px;
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
        .stButton > button {
            width: 100%;
            border-radius: 8px;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # =====================================================
    # 5. 사용자 변경 감지
    # =====================================================
    loaded_user_id = st.session_state.get("portfolio_loaded_user_id")

    if loaded_user_id != user_id:
        reset_portfolio_widget_state()
        portfolio = get_portfolio(user_id)

        if portfolio:
            load_portfolio_to_session(portfolio)
        else:
            load_default_portfolio()

        st.session_state["portfolio_loaded_user_id"] = user_id

    # =====================================================
    # 6. Header
    # =====================================================
    st.title("💰 Smart Portfolio AI PRO")
    st.caption(
        f"👤 {username}님, 환영합니다. 현재 포트폴리오를 분석하고 관리해보세요."
    )
    st.divider()

    # =====================================================
    # 7. Sidebar
    # =====================================================
    st.sidebar.header("⚙️ 포트폴리오 설정")

    # =====================================================
    # 8. 나이
    # =====================================================
    age = st.sidebar.number_input(
        "나이 (세)",
        min_value=20,
        max_value=100,
        value=st.session_state.get("age", DEFAULT_PORTFOLIO["age"]),
        step=1,
        key="age_input",
    )
    st.session_state["age"] = age

    # =====================================================
    # 9. 현재 보유 자산
    # =====================================================
    st.sidebar.subheader("💵 보유 자산")
    cash = money_input("현금", DEFAULT_PORTFOLIO["cash"])
    etf_amount = money_input("현재 ETF 금액", DEFAULT_PORTFOLIO["etf_amount"])
    bond_amount = money_input("현재 채권 금액", DEFAULT_PORTFOLIO["bond_amount"])
    pension_amount = money_input(
        "현재 연금 금액", DEFAULT_PORTFOLIO["pension_amount"]
    )

    # =====================================================
    # 10. 월 적립식 투자
    # =====================================================
    st.sidebar.subheader("📅 월 적립식 투자")
    monthly_etf = money_input("ETF 월 투자", DEFAULT_PORTFOLIO["monthly_etf"])
    monthly_bond = money_input("채권 월 투자", DEFAULT_PORTFOLIO["monthly_bond"])
    monthly_pension = money_input(
        "연금 월 투자", DEFAULT_PORTFOLIO["monthly_pension"]
    )

    # =====================================================
    # 11. ETF 데이터
    # =====================================================
    st.sidebar.subheader("📈 ETF 데이터")
    try:
        etf_api = ETFData()
        etfs = etf_api.get_etfs()
    except Exception as e:
        st.error(f"❌ ETF 데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return

    if not etfs:
        st.error("❌ ETF 데이터를 불러올 수 없습니다.")
        return

    # =====================================================
    # 12. 저장된 ETF 선택
    # =====================================================
    st.sidebar.subheader("🎯 Target ETF 선택")
    saved_etf_name = st.session_state.get("selected_etf_name")
    default_etf_index = 0

    if saved_etf_name:
        for index, etf in enumerate(etfs):
            if etf.get("name") == saved_etf_name:
                default_etf_index = index
                break

    # =====================================================
    # 13. ETF Selectbox
    # =====================================================
    selected_etf = st.sidebar.selectbox(
        "관심 ETF",
        etfs,
        index=default_etf_index,
        format_func=lambda x: x.get("name", "Unknown ETF"),
        key="selected_etf",
    )
    selected_etf = selected_etf or {}
    etf_name = selected_etf.get("name", "Unknown ETF")
    st.session_state["selected_etf_name"] = etf_name

    # =====================================================
    # 14. ETF 수익률 및 위험도
    # =====================================================
    try:
        etf_return = float(selected_etf.get("return_1y", 5.0))
    except (TypeError, ValueError):
        etf_return = 5.0

    try:
        etf_risk = int(selected_etf.get("risk", 3))
    except (TypeError, ValueError):
        etf_risk = 3

    # =====================================================
    # 16. 포트폴리오 저장
    # =====================================================
    st.sidebar.divider()
    st.sidebar.subheader("💾 포트폴리오 저장")

    if st.sidebar.button(
        "💾 현재 포트폴리오 저장",
        type="primary",
        use_container_width=True,
        key="save_portfolio_button",
    ):
        success = save_portfolio(
            user_id=user_id,
            age=age,
            cash=cash,
            etf_amount=etf_amount,
            bond_amount=bond_amount,
            pension_amount=pension_amount,
            monthly_etf=monthly_etf,
            monthly_bond=monthly_bond,
            monthly_pension=monthly_pension,
            selected_etf=etf_name,
        )

        if success:
            st.session_state["portfolio_exists"] = True
            st.session_state["portfolio_loaded_user_id"] = user_id
            st.sidebar.success("✅ 포트폴리오가 저장되었습니다.")
            st.rerun()  # 저장 후 세션/화면 즉시 최신화
        else:
            st.sidebar.error("❌ 포트폴리오 저장에 실패했습니다.")

    # =====================================================
    # 17. 총 자산 계산
    # =====================================================
    total_asset = cash + etf_amount + bond_amount + pension_amount
    monthly_total = monthly_etf + monthly_bond + monthly_pension

    # =====================================================
    # 18. KPI
    # =====================================================
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("총 자산", f"{total_asset:,} 원")
    kpi2.metric("월 총 투자액", f"{monthly_total:,} 원")
    kpi3.metric("선택 ETF", etf_name)
    kpi4.metric("연령 / 위험도", f"{age}세 / Risk {etf_risk}")

    st.write("")

    # =====================================================
    # 19. 분석 데이터
    # =====================================================
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

    # =====================================================
    # 20. Tabs
    # =====================================================
    tab1, tab2, tab3 = st.tabs(
        ["📊 자산 현황", "🤖 AI 분석 & 리스크", "📈 10년 성과 시뮬레이션"]
    )

    # =====================================================
    # TAB 1
    # =====================================================
    with tab1:
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("🍩 자산 비중 분포")
            df_pie = pd.DataFrame(
                {
                    "자산": ["현금", "ETF", "채권", "연금"],
                    "금액": [cash, etf_amount, bond_amount, pension_amount],
                }
            )

            fig_pie = px.pie(
                df_pie,
                names="자산",
                values="금액",
                hole=0.55,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig_pie.update_traces(
                textposition="inside", textinfo="percent+label"
            )
            fig_pie.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with c2:
            st.subheader("📋 자산 세부 내역")
            df_summary = pd.DataFrame(
                {
                    "자산 항목": [
                        "현금",
                        f"ETF ({etf_name})",
                        "채권 (국공채)",
                        "연금 (IRP/연금저축)",
                    ],
                    "현재 보유 금액": [
                        f"{cash:,}원",
                        f"{etf_amount:,}원",
                        f"{bond_amount:,}원",
                        f"{pension_amount:,}원",
                    ],
                    "월 적립금": [
                        "-",
                        f"{monthly_etf:,}원",
                        f"{monthly_bond:,}원",
                        f"{monthly_pension:,}원",
                    ],
                    "기대 수익률": ["-", f"{etf_return:.1f}%", "3.0%", "5.0%"],
                }
            )
            st.dataframe(
                df_summary, use_container_width=True, hide_index=True
            )

    # =====================================================
    # TAB 2
    # =====================================================
    with tab2:
        col_ai, col_risk = st.columns([1.2, 0.8])

        with col_ai:
            st.subheader("🤖 AI 진단 및 리포트")

            if st.button(
                "🚀 AI 진단 실행하기", type="primary", key="ai_diagnosis_button"
            ):
                with st.spinner("포트폴리오 분석 중..."):
                    try:
                        result = analyze_portfolio(data)
                        rec = recommend(data)
                        st.session_state["ai_result"] = result
                        st.session_state["ai_recommendation"] = rec
                    except Exception as e:
                        st.error(f"❌ AI 분석 오류: {e}")

            if "ai_result" in st.session_state:
                st.success("✔ 진단 완료")
                st.markdown("#### 📊 분석 지표")
                st.json(st.session_state["ai_result"])
                st.markdown("#### 📌 추천 전략")
                st.info(st.session_state["ai_recommendation"])
            else:
                st.caption(
                    "버튼을 누르면 AI가 현재 포트폴리오를 진단합니다."
                )

        with col_risk:
            st.subheader("⚠️ 리스크 레벨 측정")
            total_invested = etf_amount + bond_amount + pension_amount

            if total_invested == 0:
                risk_score = 0.0
            else:
                risk_score = (
                    etf_amount * etf_risk
                    + bond_amount * 1
                    + pension_amount * 2
                ) / total_invested

            if risk_score > 4:
                status_text = "공격투자형 🚨"
                status_color = "#ff5252"
            elif risk_score > 2:
                status_text = "위험중립형 ⚖️"
                status_color = "#ffb74d"
            else:
                status_text = "안정지향형 ✅"
                status_color = "#66bb6a"

            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=round(risk_score, 2),
                    title={
                        "text": f"성향: {status_text}",
                        "font": {"size": 16},
                    },
                    gauge={
                        "axis": {"range": [0, 5]},
                        "bar": {"color": status_color},
                        "steps": [
                            {
                                "range": [0, 2],
                                "color": "rgba(102,187,106,0.2)",
                            },
                            {
                                "range": [2, 4],
                                "color": "rgba(255,183,77,0.2)",
                            },
                            {"range": [4, 5], "color": "rgba(255,82,82,0.2)"},
                        ],
                    },
                )
            )

            fig_gauge.update_layout(
                height=280,
                margin=dict(t=40, b=10, l=30, r=30),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

    # =====================================================
    # TAB 3
    # =====================================================
    with tab3:
        st.subheader("📈 복리 기반 10년 자산 성장 추이")

        etf_r = etf_return / 100
        bond_r = 0.03
        pension_r = 0.05

        years = list(range(1, 11))
        values = []

        for y in years:
            # 일시금 복리
            current_etf_future = etf_amount * ((1 + etf_r) ** y)
            current_bond_future = bond_amount * ((1 + bond_r) ** y)
            current_pension_future = pension_amount * ((1 + pension_r) ** y)

            # 적립식 복리 시뮬레이션
            monthly_etf_future = simulate(y, monthly_etf, etf_r)
            monthly_bond_future = simulate(y, monthly_bond, bond_r)
            monthly_pension_future = simulate(y, monthly_pension, pension_r)

            total_future = (
                cash
                + current_etf_future
                + current_bond_future
                + current_pension_future
                + monthly_etf_future
                + monthly_bond_future
                + monthly_pension_future
            )
            values.append(total_future)

        # 금액 포맷팅 함수 (1억 이상 시 억/만원, 미만 시 천단위 콤마)
        def format_krw(val):
            val = int(val)
            eok = val // 100_000_000
            man = (val % 100_000_000) // 10_000
            if eok > 0:
                return f"{eok}억 {man:,}만원" if man > 0 else f"{eok}억원"
            return f"{val:,}원"

        df_sim = pd.DataFrame(
            {
                "연도": [f"{y}년후" for y in years],
                "예상 총 자산": values,
                "표시금액": [f"{int(v):,}원" for v in values],
                "표시금액_한글": [format_krw(v) for v in values],
            }
        )

        fig_line = px.line(
            df_sim,
            x="연도",
            y="예상 총 자산",
            markers=True,
            text="표시금액",
        )

        fig_line.update_traces(
            textposition="top center",
            line_color="#4fc3f7",
            line_width=3,
        )

        # 차트 상단 텍스트 잘림 방지 (Y축 여백 추가 및 콤마 포맷 지정)
        max_val = max(values) if values else 1
        fig_line.update_layout(
            yaxis=dict(tickformat=",", range=[0, max_val * 1.15]),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=40, b=20, l=20, r=20),
        )

        st.plotly_chart(fig_line, use_container_width=True)

        # 표 출력 시 천단위 콤마 및 한글 단위 병기
        df_sim_display = pd.DataFrame(
            {
                "연도": df_sim["연도"],
                "예상 총 자산 (원)": df_sim["표시금액"],
                "예상 총 자산 (요약)": df_sim["표시금액_한글"],
            }
        )
        st.dataframe(
            df_sim_display, use_container_width=True, hide_index=True
        )