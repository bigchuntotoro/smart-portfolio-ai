import streamlit as st

from src.core.auth import signup


def show_signup():

    st.subheader("📝 회원가입")

    with st.form("signup_form"):

        username = st.text_input(
            "아이디"
        )

        password = st.text_input(
            "비밀번호",
            type="password"
        )

        password_confirm = st.text_input(
            "비밀번호 확인",
            type="password"
        )

        submitted = st.form_submit_button(
            "회원가입",
            use_container_width=True
        )

    # ==========================================
    # 회원가입 처리
    # ==========================================

    if submitted:

        # 입력값 공백 제거
        username = username.strip()

        # 필수 입력 확인
        if not username or not password:

            st.warning(
                "아이디와 비밀번호를 입력해주세요."
            )

            return

        # 아이디 길이 확인
        if len(username) < 4:

            st.warning(
                "아이디는 4자 이상 입력해주세요."
            )

            return

        # 비밀번호 확인
        if password != password_confirm:

            st.error(
                "비밀번호가 일치하지 않습니다."
            )

            return

        # 비밀번호 길이 확인
        if len(password) < 8:

            st.warning(
                "비밀번호는 8자 이상 입력해주세요."
            )

            return

        # ==========================================
        # 회원가입
        # ==========================================

        if signup(username, password):

            st.success(
                "✅ 회원가입이 완료되었습니다."
            )

            st.info(
                "🔐 로그인 메뉴에서 로그인해주세요."
            )

        else:

            st.error(
                "❌ 이미 존재하는 아이디입니다."
            )
