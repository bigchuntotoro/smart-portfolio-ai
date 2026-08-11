import streamlit as st

from src.db.database import init_db
from src.core.auth import verify_token

from src.ui.login import show_login
from src.ui.signup import show_signup
from src.ui.dashboard import show_dashboard


# ==========================================
# 페이지 설정
# ==========================================

st.set_page_config(
    page_title="Smart Portfolio AI PRO",
    page_icon="💰",
    layout="wide"
)


# ==========================================
# DB 초기화
# ==========================================

init_db()


# ==========================================
# Session State 초기화
# ==========================================

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "login_user" not in st.session_state:
    st.session_state.login_user = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None


# ==========================================
# JWT 인증 확인
# ==========================================

def is_authenticated():

    token = st.session_state.get("access_token")

    # 토큰이 없으면 비로그인
    if not token:
        return False

    # JWT 검증
    payload = verify_token(token)

    # JWT가 만료되었거나 잘못된 경우
    if not payload:

        st.session_state.access_token = None
        st.session_state.login_user = None
        st.session_state.user_id = None

        return False

    # JWT에서 사용자 정보 복구
    username = payload.get("username")
    user_id = payload.get("sub")

    if not username or user_id is None:

        st.session_state.access_token = None
        st.session_state.login_user = None
        st.session_state.user_id = None

        return False

    st.session_state.login_user = username

    try:
        st.session_state.user_id = int(user_id)
    except (TypeError, ValueError):

        st.session_state.access_token = None
        st.session_state.login_user = None
        st.session_state.user_id = None

        return False

    return True


# ==========================================
# 로그인 상태 확인
# ==========================================

authenticated = is_authenticated()


# ==========================================
# 로그인 상태
# ==========================================

if authenticated:

    # --------------------------------------
    # 사용자 정보
    # --------------------------------------

    st.sidebar.markdown(
        f"### 👤 {st.session_state.login_user}님"
    )

    st.sidebar.divider()

    # --------------------------------------
    # 로그아웃
    # --------------------------------------

    if st.sidebar.button(
        "🚪 로그아웃",
        use_container_width=True
    ):

        st.session_state.access_token = None
        st.session_state.login_user = None
        st.session_state.user_id = None

        st.rerun()

    # --------------------------------------
    # Dashboard
    # --------------------------------------

    show_dashboard()


# ==========================================
# 비로그인 상태
# ==========================================

else:

    st.title("💰 Smart Portfolio AI PRO")

    menu = st.sidebar.selectbox(
        "🔑 접속 메뉴",
        [
            "로그인",
            "회원가입"
        ]
    )

    col1, col2, col3 = st.columns(
        [1, 2, 1]
    )

    with col2:

        if menu == "로그인":

            show_login()

        else:

            show_signup()
