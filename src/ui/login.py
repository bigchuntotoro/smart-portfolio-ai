import streamlit as st

from src.core.auth import login


def show_login():

    st.subheader("🔐 로그인")

    with st.form("login_form"):

        username = st.text_input(
            "아이디"
        )

        password = st.text_input(
            "비밀번호",
            type="password"
        )

        submitted = st.form_submit_button(
            "로그인",
            type="primary",
            use_container_width=True
        )

    # ==========================================
    # 로그인 처리
    # ==========================================

    if submitted:

        # 입력값 확인
        if not username or not password:

            st.warning(
                "아이디와 비밀번호를 입력해주세요."
            )

            return

        # 로그인 인증
        result = login(
            username,
            password
        )

        # ==========================================
        # 로그인 성공
        # ==========================================

        if result:

            # JWT 저장
            st.session_state.access_token = (
                result["access_token"]
            )

            # 사용자 ID 저장
            st.session_state.user_id = (
                result["user_id"]
            )

            # 사용자 이름 저장
            st.session_state.login_user = (
                result["username"]
            )

            st.success(
                f"{result['username']}님 환영합니다!"
            )

            # 앱 다시 실행
            st.rerun()

        # ==========================================
        # 로그인 실패
        # ==========================================

        else:

            st.error(
                "아이디 또는 비밀번호가 올바르지 않습니다."
            )
