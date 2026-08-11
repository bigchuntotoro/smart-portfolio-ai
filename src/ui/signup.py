import streamlit as st
from src.core.auth import signup


def show_signup():
    st.subheader("📝 회원가입")

    username = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")

    if st.button("회원가입"):
        if signup(username, password):
            st.success("회원가입 완료! 로그인 해주세요")
        else:
            st.error("이미 존재하는 아이디입니다")