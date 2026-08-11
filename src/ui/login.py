import streamlit as st
from src.core.auth import login


# =========================================================
# 이전 사용자 Dashboard 상태 초기화
# =========================================================

def clear_previous_user_state():
    keys_to_remove = [
        # 인증
        "access_token",
        "login_user",
        "user_id",

        # 포트폴리오 로딩 상태
        "portfolio_loaded",
        "portfolio_loaded_user_id",
        "portfolio_exists",

        # 포트폴리오 값
        "age",
        "selected_etf_name",

        "현금",
        "현재 ETF 금액",
        "현재 채권 금액",
        "현재 연금 금액",

        "ETF 월 투자",
        "채권 월 투자",
        "연금 월 투자",

        # Widget
        "age_input",

        "money_현금",
        "money_현재 ETF 금액",
        "money_현재 채권 금액",
        "money_현재 연금 금액",

        "money_ETF 월 투자",
        "money_채권 월 투자",
        "money_연금 월 투자",

        # money_input 내부값
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
# 로그인 UI
# =========================================================

def show_login(cookies):
    st.subheader("🔐 로그인")

    # =====================================================
    # 로그인 Form
    # =====================================================
    with st.form("login_form"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button(
            "로그인",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    # =====================================================
    # 입력값 검증
    # =====================================================
    username = username.strip()

    if not username:
        st.warning("⚠️ 아이디를 입력해주세요.")
        return

    if not password:
        st.warning("⚠️ 비밀번호를 입력해주세요.")
        return

    # =====================================================
    # 로그인 처리
    # =====================================================
    try:
        result = login(username, password)
    except Exception as e:
        st.error(f"❌ 로그인 처리 중 오류가 발생했습니다: {e}")
        return

    if not result:
        st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
        return

    # =====================================================
    # 이전 사용자 상태 제거
    # =====================================================
    clear_previous_user_state()

    # =====================================================
    # 로그인 정보 추출
    # =====================================================
    token = result.get("access_token")
    user_id = result.get("user_id")
    username = result.get("username")

    if not token:
        st.error("❌ 로그인 토큰을 생성하지 못했습니다.")
        return

    if user_id is None:
        st.error("❌ 사용자 ID를 확인할 수 없습니다.")
        return

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        st.error("❌ 잘못된 사용자 ID입니다.")
        return

    # =====================================================
    # Session State 저장
    # =====================================================
    st.session_state["access_token"] = token
    st.session_state["user_id"] = user_id
    st.session_state["login_user"] = username

    # 포트폴리오 상태 초기화
    st.session_state["portfolio_loaded"] = False
    st.session_state["portfolio_loaded_user_id"] = None
    st.session_state["portfolio_exists"] = False

    # =====================================================
    # ★ 브라우저 Cookie 저장
    # CookieController.set()은 (name, value) 기본 형태로 호출해야
    # TypeError 없이 브라우저 JS 컴포넌트로 전달됩니다.
    # =====================================================
    try:
        cookies.set("access_token", token)
    except Exception as e:
        st.error(f"❌ 로그인 쿠키 저장 실패: {e}")
        return

    # =====================================================
    # 로그인 완료 후 대시보드 진입
    # 즉시 st.rerun()을 호출하면 JS 쿠키 전송이 차단되므로
    # 버튼 클릭 또는 안전한 이동을 유도합니다.
    # =====================================================
    st.success(f"✅ {username}님 환영합니다!")

    if st.button("🚀 대시보드로 이동", type="primary", use_container_width=True):
        st.rerun()