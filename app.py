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

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "login_user" not in st.session_state:
    st.session_state.login_user = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "portfolio_loaded" not in st.session_state:
    st.session_state.portfolio_loaded = False


# =========================================================
# JWT 인증 확인
# =========================================================

def is_authenticated():

    # -----------------------------------------------------
    # 1. Session State에서 JWT 확인
    # -----------------------------------------------------

    token = st.session_state.get("access_token")


    # -----------------------------------------------------
    # 2. Session State에 없으면 Cookie에서 복원
    # -----------------------------------------------------

    if not token:

        try:
            token = cookies.get("access_token")
        except Exception:
            token = None


    # -----------------------------------------------------
    # 3. JWT가 없으면 비로그인
    # -----------------------------------------------------

    if not token:

        return False


    # -----------------------------------------------------
    # 4. JWT 검증
    # -----------------------------------------------------

    payload = verify_token(token)


    # -----------------------------------------------------
    # 5. JWT가 만료되었거나 잘못된 경우
    # -----------------------------------------------------

    if not payload:

        st.session_state.access_token = None
        st.session_state.login_user = None
        st.session_state.user_id = None
        st.session_state.portfolio_loaded = False

        try:
            cookies.remove("access_token")
        except Exception:
            pass

        return False


    # -----------------------------------------------------
    # 6. JWT 사용자 정보 확인
    # -----------------------------------------------------

    username = payload.get("username")
    user_id = payload.get("sub")


    if not username or user_id is None:

        st.session_state.access_token = None
        st.session_state.login_user = None
        st.session_state.user_id = None
        st.session_state.portfolio_loaded = False

        try:
            cookies.remove("access_token")
        except Exception:
            pass

        return False


    # -----------------------------------------------------
    # 7. user_id 변환
    # -----------------------------------------------------

    try:

        user_id = int(user_id)

    except (TypeError, ValueError):

        st.session_state.access_token = None
        st.session_state.login_user = None
        st.session_state.user_id = None
        st.session_state.portfolio_loaded = False

        try:
            cookies.remove("access_token")
        except Exception:
            pass

        return False


    # -----------------------------------------------------
    # 8. Session State 복원
    # -----------------------------------------------------

    st.session_state.access_token = token
    st.session_state.login_user = username
    st.session_state.user_id = user_id


    return True


# =========================================================
# 로그인 상태 확인
# =========================================================

authenticated = is_authenticated()


# =========================================================
# 로그인 상태
# =========================================================

if authenticated:

    # -----------------------------------------------------
    # 사용자 정보
    # -----------------------------------------------------

    st.sidebar.markdown(
        f"### 👤 {st.session_state.login_user}님"
    )

    st.sidebar.divider()


    # -----------------------------------------------------
    # 로그아웃
    # -----------------------------------------------------

    if st.sidebar.button(
        "🚪 로그아웃",
        use_container_width=True,
    ):

        # Session State 삭제
        st.session_state.access_token = None
        st.session_state.login_user = None
        st.session_state.user_id = None

        # 포트폴리오 관련 Session State 초기화
        st.session_state.portfolio_loaded = False

        # Cookie 삭제
        try:
            cookies.remove("access_token")
        except Exception:
            pass

        st.rerun()


    # -----------------------------------------------------
    # Dashboard
    # -----------------------------------------------------

    show_dashboard()


# =========================================================
# 비로그인 상태
# =========================================================

else:

    st.title("💰 Smart Portfolio AI PRO")

    menu = st.sidebar.selectbox(
        "🔑 접속 메뉴",
        [
            "로그인",
            "회원가입",
        ],
    )


    col1, col2, col3 = st.columns(
        [1, 2, 1]
    )


    with col2:

        if menu == "로그인":

            show_login()

        else:

            show_signup()
