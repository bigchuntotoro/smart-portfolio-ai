import streamlit as st
from streamlit_cookies_controller import CookieController

from src.core.auth import login


cookies = CookieController()


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


    if submitted:

        if not username or not password:

            st.warning(
                "아이디와 비밀번호를 입력해주세요."
            )

            return


        result = login(
            username,
            password
        )


        if result:

            token = result["access_token"]


            # -----------------------------------------
            # Session State 저장
            # -----------------------------------------

            st.session_state.access_token = token

            st.session_state.user_id = (
                result["user_id"]
            )

            st.session_state.login_user = (
                result["username"]
            )


            # -----------------------------------------
            # 브라우저 Cookie 저장
            # -----------------------------------------

            cookies.set(
                "access_token",
                token,
                max_age=60 * 60,
            )


            # -----------------------------------------
            # 포트폴리오 자동 복원을 위해 초기화
            # -----------------------------------------

            st.session_state.portfolio_loaded = False


            st.success(
                f"{result['username']}님 환영합니다!"
            )


            st.rerun()


        else:

            st.error(
                "아이디 또는 비밀번호가 올바르지 않습니다."
            )
