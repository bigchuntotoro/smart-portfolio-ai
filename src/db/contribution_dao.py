import sqlite3
from typing import Dict, Any
from src.db.database import get_connection

# 기본 세팅값 (데이터가 없을 때 반환)
DEFAULT_PLAN = {
    "p_sp500": 300_000,
    "p_nasdaq": 300_000,
    "p_dividend": 600_000,
    "i_high_div": 180_000,
    "i_cover_call": 240_000,
    "i_bond": 900_000,
    "start_month": 9,
    "end_month": 12,
}


def get_user_plan(user_id: int) -> Dict[str, Any]:
    """
    사용자의 연금 납입 플랜을 DB에서 조회합니다.
    저장된 데이터가 없으면 기본값(DEFAULT_PLAN)을 반환합니다.
    """
    query = """
    SELECT p_sp500, p_nasdaq, p_dividend, 
           i_high_div, i_cover_call, i_bond, 
           start_month, end_month
    FROM contribution_plans
    WHERE user_id = ?
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        else:
            return DEFAULT_PLAN.copy()
    except Exception as e:
        print(f"[DB ERROR] get_user_plan 실패 (user_id: {user_id}): {e}")
        return DEFAULT_PLAN.copy()
    finally:
        if conn:
            conn.close()


def save_user_plan(user_id: int, plan_data: Dict[str, Any]) -> bool:
    """
    사용자의 연금 납입 플랜을 DB에 저장/업데이트(Upsert)합니다.
    """
    query = """
    INSERT INTO contribution_plans (
        user_id, p_sp500, p_nasdaq, p_dividend,
        i_high_div, i_cover_call, i_bond,
        start_month, end_month, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(user_id) DO UPDATE SET
        p_sp500 = EXCLUDED.p_sp500,
        p_nasdaq = EXCLUDED.p_nasdaq,
        p_dividend = EXCLUDED.p_dividend,
        i_high_div = EXCLUDED.i_high_div,
        i_cover_call = EXCLUDED.i_cover_call,
        i_bond = EXCLUDED.i_bond,
        start_month = EXCLUDED.start_month,
        end_month = EXCLUDED.end_month,
        updated_at = CURRENT_TIMESTAMP;
    """

    params = (
        user_id,
        plan_data.get("p_sp500", 300_000),
        plan_data.get("p_nasdaq", 300_000),
        plan_data.get("p_dividend", 600_000),
        plan_data.get("i_high_div", 180_000),
        plan_data.get("i_cover_call", 240_000),
        plan_data.get("i_bond", 900_000),
        plan_data.get("start_month", 9),
        plan_data.get("end_month", 12),
    )

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB ERROR] save_user_plan 실패 (user_id: {user_id}): {e}")
        return False
    finally:
        if conn:
            conn.close()