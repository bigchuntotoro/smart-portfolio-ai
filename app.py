import streamlit as st
from streamlit_cookies_controller import CookieController

from src.core.auth import refresh_access_token, verify_token
from src.core.session_keys import clear_auth_cookies, clear_user_session_keys
from src.db.database import init_db
from src.ui.contribution_dashboard import show_pension_dashboard
from src.ui.login import show_login
from src.ui.signup import show_signup
from src.ui.rebalancing import show_rebalancing_dashboard
from src.ui.simulation import show_asset_simulation

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
    # 납입 기간 기본값
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
    """로그아웃 또는 다른 사용자 로그인 시 이전 사용자의 Session State를 모두 제거합니다."""
    clear_user_session_keys()


# =========================================================
# JWT 인증 확인
# =========================================================

def is_authenticated() -> bool:
    """인증 처리 순서:

    1. Session State의 Access Token 확인
    2. Access Token이 없으면 Cookie의 Refresh Token 확인 후 재발급
    3. JWT 토큰 검증
    4. 사용자 ID / username Session State 동기화
    """

    token = st.session_state.get("access_token")
    user_id = st.session_state.get("user_id")

    # =====================================================
    # 1. Access Token이 없는 경우 Refresh Token으로 재발급 시도
    # =====================================================
    if not token:
        try:
            refresh_token = cookies.get("refresh_token")
        except Exception as e:
            print(f"Refresh Token Cookie 읽기 오류: {e}")
            refresh_token = None

        if user_id is None:
            try:
                cookie_user_id = cookies.get("user_id")
                if cookie_user_id is not None:
                    user_id = int(cookie_user_id)
            except (Exception, TypeError, ValueError) as e:
                print(f"user_id 쿠키 읽기 오류: {e}")
                user_id = None

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
    # 2. Token이 없으면 비로그인 처리
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

    if not payload:
        clear_user_session()
        clear_auth_cookies(cookies)
        return False

    # =====================================================
    # 4. JWT 페이로드 파싱 및 검증
    # =====================================================
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

    # =====================================================
    # 5. 사용자 교체 감지 및 Session State 동기화
    # =====================================================
    old_user_id = st.session_state.get("user_id")
    if old_user_id is not None and int(old_user_id) != valid_user_id:
        clear_user_session()

    st.session_state["access_token"] = token
    st.session_state["login_user"] = username
    st.session_state["user_id"] = valid_user_id

    return True

# =========================================================
# 로그인 상태 확인
# =========================================================

authenticated = is_authenticated()

# =========================================================
# 메인 렌더링 영역
# =========================================================

if authenticated:
    current_user_id = st.session_state.get("user_id")
    current_username = st.session_state.get("login_user")

    # -----------------------------------------------------
    # Sidebar 로그인 사용자 정보 & 메인 메뉴
    # -----------------------------------------------------
    st.sidebar.markdown(f"### 👤 {current_username}님")
    st.sidebar.caption("Smart Portfolio AI PRO")
    st.sidebar.divider()

    # 왼쪽 내비게이션 메뉴 라디오 버튼 추가
    main_menu = st.sidebar.radio(
        "📌 서비스 메뉴",
        [
            "💰 통합 연금 납입 대시보드",
            "⚖️ 포트폴리오 리밸런싱",
            "📊 자산 시뮬레이션",
        ],
        key="main_navigation_menu",
    )

    st.sidebar.divider()

    # 로그아웃 버튼
    if st.sidebar.button("🚪 로그아웃", use_container_width=True, key="logout_button"):
        clear_auth_cookies(cookies)
        clear_user_session()
        st.rerun()

    # -----------------------------------------------------
    # 선택된 메뉴에 따른 메인 화면 렌더링 (라우팅)
    # -----------------------------------------------------
    if main_menu == "💰 통합 연금 납입 대시보드":
        show_pension_dashboard(user_id=current_user_id, cookies=cookies)

    elif main_menu == "⚖️ 포트폴리오 리밸런싱":
        show_rebalancing_dashboard(user_id=current_user_id, cookies=cookies)

    elif main_menu == "📊 자산 시뮬레이션":
        show_asset_simulation(user_id=current_user_id, cookies=cookies)

else:
    st.title("💰 Smart Portfolio AI PRO")
    st.caption("연금저축 + IRP 납입 계획 및 포트폴리오 자산 관리")
    st.divider()

    # 로그인 / 회원가입 선택
    menu = st.sidebar.selectbox(
        "🔑 접속 메뉴",
        ["로그인", "회원가입"],
        key="auth_menu",
    )

    # 로그인 / 회원가입 화면
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if menu == "로그인":
            show_login(cookies)
        else:
            show_signup()