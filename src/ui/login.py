import streamlit as st
from src.core.auth import login


def show_login():
    st.subheader("🔐 로그인")

    username = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")

    if st.button("로그인"):
        if login(username, password):
            st.session_state.user = username
            st.success("로그인 성공!")
            st.rerun()
        else:
            st.error("아이디 또는 비밀번호 오류")