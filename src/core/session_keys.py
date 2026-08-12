"""
Streamlit session_state / 쿠키에서 사용하는 키를 한 곳에서 관리합니다.
로그아웃, 재로그인, 계정 전환 시 지워야 할 키 목록이 여러 파일에
중복 정의되어 있으면 한쪽만 고치고 다른 쪽을 빠뜨리는 실수가 반복되므로,
이 파일 하나만 수정하면 main.py / login.py 양쪽에 자동으로 반영됩니다.
"""

import streamlit as st

# =========================================================
# 인증 관련 키
# =========================================================
AUTH_KEYS = [
    "access_token",
    "login_user",
    "user_id",
    "auth_menu",
]

# =========================================================
# 연금 납입 계획 대시보드(show_pension_dashboard) 키
# src/ui/contribution_dashboard.py 와 반드시 동기화되어야 합니다.
# =========================================================
PENSION_KEYS = [
    "loaded_user_id",
    "p_sp500",
    "p_nasdaq",
    "p_dividend",
    "i_high_div",
    "i_cover_call",
    "i_bond",
    "start_month",
    "end_month",
]

# =========================================================
# 구버전 호환용 키 (레거시 대시보드 흔적 - 남아있을 경우 대비)
# =========================================================
LEGACY_KEYS = [
    "portfolio_loaded",
    "portfolio_loaded_user_id",
    "portfolio_exists",
    "age",
    "selected_etf_name",
    "age_input",
    "현금", "현재 ETF 금액", "현재 채권 금액", "현재 연금 금액",
    "ETF 월 투자", "채권 월 투자", "연금 월 투자",
    "money_현금", "money_현재 ETF 금액", "money_현재 채권 금액", "money_현재 연금 금액",
    "money_ETF 월 투자", "money_채권 월 투자", "money_연금 월 투자",
    "money_value_현금", "money_value_현재 ETF 금액", "money_value_현재 채권 금액",
    "money_value_현재 연금 금액", "money_value_ETF 월 투자", "money_value_채권 월 투자",
    "money_value_연금 월 투자",
    "selected_etf",
    "ai_diagnosis_result", "ai_result", "ai_recommendation",
    "pension_sp500_v2", "pension_nasdaq_v2", "pension_dividend_v2",
    "irp_high_dividend_v2", "irp_cover_call_v2", "irp_bond_v2",
    "contribution_start_month", "contribution_end_month",
    "pension_current", "irp_current",
]

# =========================================================
# 로그아웃 / 계정 전환 시 지워야 할 전체 키
# =========================================================
ALL_USER_SESSION_KEYS = AUTH_KEYS + PENSION_KEYS + LEGACY_KEYS


def clear_user_session_keys():
    """로그아웃 또는 다른 사용자 로그인 시 session_state를 정리합니다."""
    for key in ALL_USER_SESSION_KEYS:
        st.session_state.pop(key, None)


def clear_auth_cookies(cookies):
    """refresh_token, user_id 쿠키를 정리합니다. 실패해도 조용히 무시합니다."""
    try:
        cookies.remove("refresh_token", path="/")
        cookies.remove("user_id", path="/")
    except Exception as e:
        print(f"Cookie 삭제 오류: {e}")