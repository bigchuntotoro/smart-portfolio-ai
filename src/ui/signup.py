import streamlit as st

# DAO를 직접 호출하지 않고 Auth 서비스의 signup 함수를 호출합니다.
# (프로젝트 구조에 맞게 import 경로를 확인해 주세요. 예: src.auth, src.services.auth 등)
from src.core.auth import signup


# =========================================================
# 회원가입 화면
# =========================================================

def show_signup():

    st.subheader("📝 회원가입")

    # =====================================================
    # 회원가입 입력
    # =====================================================

    username = st.text_input(
        "아이디",
        key="signup_username",
    )

    password = st.text_input(
        "비밀번호",
        type="password",
        key="signup_password",
    )

    password_confirm = st.text_input(
        "비밀번호 확인",
        type="password",
        key="signup_password_confirm",
    )

    # =====================================================
    # 회원가입 버튼
    # =====================================================

    if st.button(
        "회원가입",
        key="signup_button",
        use_container_width=True,
    ):

        # -------------------------------------------------
        # 입력값 검증
        # -------------------------------------------------

        username = username.strip()

        if not username:

            st.error(
                "❌ 아이디를 입력하세요."
            )

            return

        if not password:

            st.error(
                "❌ 비밀번호를 입력하세요."
            )

            return

        if not password_confirm:

            st.error(
                "❌ 비밀번호 확인을 입력하세요."
            )

            return

        if password != password_confirm:

            st.error(
                "❌ 비밀번호가 일치하지 않습니다."
            )

            return

        # -------------------------------------------------
        # 회원가입 처리 (Auth 서비스 layer 호출 -> 비밀번호 해싱 후 DB 저장)
        # -------------------------------------------------

        user_id = signup(
            username,
            password,
        )

        # -------------------------------------------------
        # 회원가입 성공
        # -------------------------------------------------

        if user_id:

            # 기존 로그인 세션 제거
            st.session_state.pop(
                "user_id",
                None,
            )

            st.session_state.pop(
                "username",
                None,
            )

            st.session_state.pop(
                "login_user",
                None,
            )

            st.session_state[
                "logged_in"
            ] = False

            # -------------------------------------------------
            # 포트폴리오 세션 제거
            # -------------------------------------------------

            st.session_state.pop(
                "portfolio_loaded_user_id",
                None,
            )

            st.session_state.pop(
                "portfolio_exists",
                None,
            )

            # -------------------------------------------------
            # 회원가입 성공 메시지
            # -------------------------------------------------

            st.success(
                f"✅ '{username}' 회원가입이 완료되었습니다!"
            )

            st.info(
                "🔐 회원가입이 완료되었습니다. "
                "아래 로그인 화면에서 새 계정으로 로그인해주세요."
            )

        # -------------------------------------------------
        # 회원가입 실패
        # -------------------------------------------------

        else:

            st.error(
                "❌ 회원가입에 실패했습니다."
            )

            st.warning(
                f"⚠️ '{username}' 아이디가 이미 존재하거나 "
                "DB 저장 중 오류가 발생했을 수 있습니다."
            )