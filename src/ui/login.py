import streamlit as st
from src.core.auth import login
from src.core.session_keys import clear_user_session_keys


def show_login(cookies):
    st.subheader("🔐 로그인")

    with st.form("login_form"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

    if not submitted:
        return

    username = username.strip()

    if not username:
        st.warning("⚠️ 아이디를 입력해주세요.")
        return

    if not password:
        st.warning("⚠️ 비밀번호를 입력해주세요.")
        return

    try:
        result = login(username, password)
    except Exception as e:
        st.error(f"❌ 로그인 처리 중 오류가 발생했습니다: {e}")
        return

    if not result:
        st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
        return

    # 이전 사용자 상태 제거 (연금 대시보드 키 포함, session_keys.py 참조)
    clear_user_session_keys()

    access_token = result.get("access_token")
    refresh_token = result.get("refresh_token")
    user_id = result.get("user_id")
    username = result.get("username")

    if not access_token or not refresh_token:
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

    st.session_state["access_token"] = access_token
    st.session_state["user_id"] = user_id
    st.session_state["login_user"] = username

    try:
        cookies.set("refresh_token", refresh_token)
        cookies.set("user_id", str(user_id))
    except Exception as e:
        st.error(f"❌ Refresh Token 쿠키 저장 실패: {e}")
        return

    st.success(f"✅ {username}님 환영합니다!")

    if st.button("🚀 대시보드로 이동", type="primary", use_container_width=True):
        st.rerun()