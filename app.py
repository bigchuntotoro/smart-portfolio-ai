import streamlit as st
from streamlit_cookies_controller import CookieController

from src.core.auth import refresh_access_token, verify_token
from src.db.database import init_db

from src.ui.login import show_login
from src.ui.signup import show_signup
from src.ui.contribution_dashboard import show_pension_dashboard
from src.core.session_keys import clear_auth_cookies, clear_user_session_keys

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

    # -------------------------------------------------
    # 연금저축 ETF별 현재 납입액 (Session Keys)
    # -------------------------------------------------
    "p_sp500": 300_000,
    "p_nasdaq": 300_000,
    "p_dividend": 600_000,

    # -------------------------------------------------
    # IRP ETF별 현재 납입액 (Session Keys)
    # -------------------------------------------------
    "i_high_div": 180_000,
    "i_cover_call": 240_000,
    "i_bond": 900_000,

    # -------------------------------------------------
    # 납입 기간
    # -------------------------------------------------
    "start_month": 9,
    "end_month": 12,
}


for key, value in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# 사용자 Session 초기화
# =========================================================

def clear_user_session():
    """
    로그아웃 또는 다른 사용자 로그인 시
    이전 사용자의 Session State를 모두 제거합니다.
    """
    clear_user_session_keys()

# =========================================================
# JWT 인증 확인
# =========================================================

def is_authenticated():
    """
    인증 순서

    1. Session State의 Access Token 확인
    2. Access Token이 없으면 Cookie의 Refresh Token 확인
    3. Refresh Token으로 Access Token 재발급
    4. JWT 검증
    5. 사용자 ID / username Session State 동기화
    """

    token = st.session_state.get("access_token")
    user_id = st.session_state.get("user_id")

    # =====================================================
    # 1. Access Token이 없는 경우
    # =====================================================
    if not token:
        try:
            refresh_token = cookies.get("refresh_token")
        except Exception as e:
            print(f"Refresh Token Cookie 읽기 오류: {e}")
            refresh_token = None

        # -------------------------------------------------
        # Cookie에서 user_id 복구
        # -------------------------------------------------
        if user_id is None:
            try:
                cookie_user_id = cookies.get("user_id")
                if cookie_user_id is not None:
                    user_id = int(cookie_user_id)
            except (Exception, TypeError, ValueError) as e:
                print(f"user_id 쿠키 읽기 오류: {e}")
                user_id = None

        # -------------------------------------------------
        # Refresh Token으로 Access Token 재발급
        # -------------------------------------------------
        if refresh_token:
            try:
                res = refresh_access_token(user_id, refresh_token)
                if res and res.get("access_token"):
                    token = res["access_token"]
                    st.session_state["access_token"] = token
                    if user_id is not None:
                        st.session_state["user_id"] = user_id
            except Exception as e:
                print(f"Token Refresh 실패: {e}")
                token = None

    # =====================================================
    # 2. Token이 없으면 비로그인
    # =====================================================
    if not token:
        return False

    # =====================================================
    # 3. JWT 검증
    # =====================================================
    try:
        payload = verify_token(token)
    except Exception as e:
        print(f"JWT 검증 오류: {e}")
        payload = None

    # =====================================================
    # 4. JWT가 유효하지 않음
    # =====================================================
    if not payload:
        clear_user_session()
        clear_auth_cookies(cookies)
        return False

    username = payload.get("username")
    token_user_id = payload.get("sub")

    if not username or token_user_id is None:
        clear_user_session()
        clear_auth_cookies(cookies)
        return False

    try:
        valid_user_id = int(token_user_id)
    except (TypeError, ValueError):
        clear_user_session()
        clear_auth_cookies(cookies)
        return False

    old_user_id = st.session_state.get("user_id")
    if old_user_id is not None and int(old_user_id) != valid_user_id:
        clear_user_session()

    return True

    # =====================================================
    # 5. JWT 사용자 정보
    # =====================================================
    username = payload.get("username")
    token_user_id = payload.get("sub")

    if not username or token_user_id is None:
        clear_user_session()
        try:
            cookies.remove("refresh_token", path="/")
            cookies.remove("user_id", path="/")
        except Exception:
            pass
        return False

    # =====================================================
    # 6. 사용자 ID 변환
    # =====================================================
    try:
        valid_user_id = int(token_user_id)
    except (TypeError, ValueError):
        clear_user_session()
        try:
            cookies.remove("refresh_token", path="/")
            cookies.remove("user_id", path="/")
        except Exception:
            pass
        return False

    # =====================================================
    # 7. 다른 사용자 로그인 감지
    # =====================================================
    old_user_id = st.session_state.get("user_id")

    if old_user_id is not None and int(old_user_id) != valid_user_id:
        clear_user_session()

    # =====================================================
    # 8. Session State 동기화
    # =====================================================
    st.session_state["access_token"] = token
    st.session_state["login_user"] = username
    st.session_state["user_id"] = valid_user_id

    return True


# =========================================================
# 로그인 상태 확인
# =========================================================

authenticated = is_authenticated()


# =========================================================
# 로그인 상태
# =========================================================

if authenticated:
    current_user_id = st.session_state.get("user_id")
    current_username = st.session_state.get("login_user")

    # =====================================================
    # Sidebar 사용자 정보
    # =====================================================
    st.sidebar.markdown(f"### 👤 {current_username}님")
    st.sidebar.divider()

    # =====================================================
    # 로그아웃
    # =====================================================
    if st.sidebar.button("🚪 로그아웃", use_container_width=True, key="logout_button"):
        clear_auth_cookies(cookies)
        clear_user_session()
        st.rerun()

    # =====================================================
    # 로그인 후 화면 (통합 연금 납입 계획 표시)
    # =====================================================
    show_pension_dashboard(user_id=current_user_id, cookies=cookies)


# =========================================================
# 비로그인 상태
# =========================================================

else:
    st.title("💰 Smart Portfolio AI PRO")
    st.caption("연금저축 + IRP 납입 계획 관리")
    st.divider()

    # =====================================================
    # 로그인 / 회원가입 선택
    # =====================================================
    menu = st.sidebar.selectbox(
        "🔑 접속 메뉴",
        ["로그인", "회원가입"],
        key="auth_menu",
    )

    # =====================================================
    # 로그인 / 회원가입 화면
    # =====================================================
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if menu == "로그인":
            show_login(cookies)
        else:
            show_signup()