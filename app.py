import streamlit as st
from streamlit_cookies_controller import CookieController

from src.db.database import init_db
from src.core.auth import verify_token

from src.ui.login import show_login
from src.ui.signup import show_signup
from src.ui.dashboard import show_dashboard


# =========================================================
# 페이지 설정
# =========================================================

st.set_page_config(
    page_title="Smart Portfolio AI PRO",
    page_icon="💰",
    layout="wide",
)


# =========================================================
# DB 초기화
# =========================================================

init_db()


# =========================================================
# Cookie Controller
# =========================================================

cookies = CookieController()


# =========================================================
# Session State 초기화
# =========================================================

DEFAULT_SESSION_STATE = {
    "access_token": None,
    "login_user": None,
    "user_id": None,

    # Portfolio
    "portfolio_loaded": False,
    "portfolio_loaded_user_id": None,
    "portfolio_exists": False,
}

for key, value in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# 사용자 Session 초기화
# =========================================================

def clear_user_session():
    keys_to_remove = [
        # 인증
        "access_token",
        "login_user",
        "user_id",

        # Portfolio
        "portfolio_loaded",
        "portfolio_loaded_user_id",
        "portfolio_exists",

        "age",
        "selected_etf_name",

        # 나이 Widget
        "age_input",

        # 금액
        "현금",
        "현재 ETF 금액",
        "현재 채권 금액",
        "현재 연금 금액",

        # 월 투자
        "ETF 월 투자",
        "채권 월 투자",
        "연금 월 투자",

        # money_input Widget
        "money_현금",
        "money_현재 ETF 금액",
        "money_현재 채권 금액",
        "money_현재 연금 금액",

        "money_ETF 월 투자",
        "money_채권 월 투자",
        "money_연금 월 투자",

        # money_input 내부 상태
        "money_value_현금",
        "money_value_현재 ETF 금액",
        "money_value_현재 채권 금액",
        "money_value_현재 연금 금액",

        "money_value_ETF 월 투자",
        "money_value_채권 월 투자",
        "money_value_연금 월 투자",

        # ETF
        "selected_etf",

        # AI
        "ai_diagnosis_result",
        "ai_result",
        "ai_recommendation",
    ]

    for key in keys_to_remove:
        st.session_state.pop(key, None)


# =========================================================
# JWT 인증 확인
# =========================================================

def is_authenticated():

    # -----------------------------------------------------
    # 1. Session State에서 JWT 확인
    # -----------------------------------------------------
    token = st.session_state.get("access_token")

    # -----------------------------------------------------
    # 2. Session에 JWT가 없으면 Cookie에서 복원
    # -----------------------------------------------------
    if not token:
        try:
            token = cookies.get("access_token")
        except Exception as e:
            print(f"Cookie 읽기 오류: {e}")
            token = None

    # -----------------------------------------------------
    # 3. JWT가 없으면 비로그인 처리
    # -----------------------------------------------------
    if not token:
        return False

    # -----------------------------------------------------
    # 4. JWT 검증
    # -----------------------------------------------------
    try:
        payload = verify_token(token)
    except Exception as e:
        print(f"JWT 검증 오류: {e}")
        return False

    # -----------------------------------------------------
    # 5. JWT가 유효하지 않은 경우만 세션/쿠키 파기
    # -----------------------------------------------------
    if not payload:
        clear_user_session()
        try:
            cookies.remove("access_token", path="/")
        except Exception:
            pass
        return False

    # -----------------------------------------------------
    # 6. JWT 사용자 정보 추출
    # -----------------------------------------------------
    username = payload.get("username")
    user_id = payload.get("sub")

    if not username or user_id is None:
        clear_user_session()
        try:
            cookies.remove("access_token", path="/")
        except Exception:
            pass
        return False

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        clear_user_session()
        try:
            cookies.remove("access_token", path="/")
        except Exception:
            pass
        return False

    # -----------------------------------------------------
    # 7. 다른 계정으로 변경된 경우 기존 포트폴리오 세션만 초기화
    # -----------------------------------------------------
    old_user_id = st.session_state.get("user_id")
    if old_user_id is not None and int(old_user_id) != user_id:
        clear_user_session()

    # -----------------------------------------------------
    # 8. Session State 동기화 및 인증 성공
    # -----------------------------------------------------
    st.session_state["access_token"] = token
    st.session_state["login_user"] = username
    st.session_state["user_id"] = user_id

    return True


# =========================================================
# 로그인 상태 확인 및 분기
# =========================================================

authenticated = is_authenticated()


if authenticated:
    current_user_id = st.session_state.get("user_id")
    current_username = st.session_state.get("login_user")

    # 사이드바 사용자 정보
    st.sidebar.markdown(f"### 👤 {current_username}님")
    st.sidebar.divider()

    # 로그아웃 버튼
    if st.sidebar.button(
        "🚪 로그아웃",
        use_container_width=True,
        key="logout_button",
    ):
        try:
            cookies.remove("access_token")
        except Exception as e:
            print(f"Cookie 삭제 오류: {e}")

        clear_user_session()
        st.rerun()

    # 대시보드 출력
    show_dashboard(current_user_id)

else:
    st.title("💰 Smart Portfolio AI PRO")

    menu = st.sidebar.selectbox(
        "🔑 접속 메뉴",
        ["로그인", "회원가입"],
        key="auth_menu",
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if menu == "로그인":
            show_login(cookies)
        else:
            show_signup()