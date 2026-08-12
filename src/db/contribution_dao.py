import json
import sqlite3
from typing import Any, Dict

from src.db.database import get_connection

# 기본 세팅값 (ETF별 1~12월 0원 배열)
DEFAULT_MONTHLY_DATA = {
    "p_sp500": [0] * 12,
    "p_nasdaq": [0] * 12,
    "p_dividend": [0] * 12,
    "i_high_div": [0] * 12,
    "i_cover_call": [0] * 12,
    "i_bond": [0] * 12,
}

DEFAULT_PLAN = {
    "start_month": 9,
    "end_month": 12,
    "monthly_data": DEFAULT_MONTHLY_DATA,
}


def get_user_plan(user_id: int) -> Dict[str, Any]:
    """사용자의 월별 연금 납입 플랜을 DB에서 조회합니다.

    데이터가 없거나 파싱 오류 발생 시 기본값을 반환합니다.
    """
    query = """
    SELECT monthly_data, start_month, end_month
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
            raw_json = row["monthly_data"]
            monthly_data = json.loads(raw_json) if raw_json else DEFAULT_MONTHLY_DATA.copy()
            return {
                "start_month": row["start_month"],
                "end_month": row["end_month"],
                "monthly_data": monthly_data,
            }
        else:
            return DEFAULT_PLAN.copy()
    except Exception as e:
        print(f"[DB ERROR] get_user_plan 실패 (user_id: {user_id}): {e}")
        return DEFAULT_PLAN.copy()
    finally:
        if conn:
            conn.close()


def save_user_plan(user_id: int, plan_data: Dict[str, Any]) -> bool:
    """사용자의 월별 연금 납입 플랜을 DB에 저장/업데이트(Upsert)합니다."""
    query = """
    INSERT INTO contribution_plans (
        user_id, monthly_data, start_month, end_month, updated_at
    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(user_id) DO UPDATE SET
        monthly_data = EXCLUDED.monthly_data,
        start_month = EXCLUDED.start_month,
        end_month = EXCLUDED.end_month,
        updated_at = CURRENT_TIMESTAMP;
    """

    monthly_data = plan_data.get("monthly_data", DEFAULT_MONTHLY_DATA)

    monthly_data = plan_data.get(
    "monthly_data",
    DEFAULT_MONTHLY_DATA
    )

    # 모든 납입액을 Python int로 변환
    clean_monthly_data = {}

    for key, values in monthly_data.items():
        clean_monthly_data[key] = [
            int(v) if v is not None else 0
            for v in values
        ]

    monthly_json_str = json.dumps(
        clean_monthly_data,
        ensure_ascii=False
    )

    params = (
        user_id,
        monthly_json_str,
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