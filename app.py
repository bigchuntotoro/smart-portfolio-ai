import streamlit as st

from src.db.database import init_db
from src.ui.login import show_login
from src.ui.signup import show_signup
from src.ui.dashboard import show_dashboard


# ========================================
# 1. 페이지 설정
# ========================================

st.set_page_config(
    page_title="Smart Portfolio AI PRO",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ========================================
# 2. DB 초기화
# ========================================

init_db()


# ========================================
# 3. 세션 초기화
# ========================================

if "user" not in st.session_state:
    st.session_state.user = None


# ========================================
# 4. 로그인 / 회원가입 / 대시보드
# ========================================

if st.session_state.user:

    show_dashboard()

else:

    menu = ["로그인", "회원가입"]

    choice = st.sidebar.selectbox(
        "메뉴",
        menu,
    )

    if choice == "로그인":
        show_login()

    else:
        show_signup()