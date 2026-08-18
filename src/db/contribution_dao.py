import json
import sqlite3
from typing import Any, Dict

from src.db.database import get_connection

# 관리 대상 연도 (대시보드와 동일하게 유지)
YEARS = [2026, 2027, 2028, 2029, 2030]

# 연도별 기본 시작/종료월 (2026년만 9~12월, 나머지는 1~12월 전체)
DEFAULT_START_END = {
    2026: (9, 12),
}

# 기본 세팅값 (ETF별 1~12월 0원 배열) - ISA 항목 추가
DEFAULT_MONTHLY_DATA = {
    "p_sp500": [0] * 12,
    "p_nasdaq": [0] * 12,
    "p_dividend": [0] * 12,
    "i_high_div": [0] * 12,
    "i_cover_call": [0] * 12,
    "i_bond": [0] * 12,
    "isa_sp500": [0] * 12,
    "isa_nasdaq": [0] * 12,
    "isa_semicon": [0] * 12,
}


def _default_monthly_data() -> Dict[str, Any]:
    return {k: v.copy() for k, v in DEFAULT_MONTHLY_DATA.items()}


def _default_yearly_plan() -> Dict[str, Any]:
    """연도별 기본 플랜 전체를 생성합니다. 반환 형태: {"2026": {...}, "2027": {...}, ...}"""
    plan = {}
    for year in YEARS:
        start, end = DEFAULT_START_END.get(year, (1, 12))
        plan[str(year)] = {
            "start_month": start,
            "end_month": end,
            "monthly_data": _default_monthly_data(),
        }
    return plan


def get_user_plan(user_id: int) -> Dict[str, Any]:
    """사용자의 연도별(2026~2030) 연금 및 ISA 납입 플랜을 DB에서 조회합니다.

    반환 형태: {"2026": {"start_month":.., "end_month":.., "monthly_data": {...}}, "2027": {...}, ...}
    데이터가 없는 연도는 기본값으로 채워서 반환하고, 조회/파싱 오류 시 전체 기본값을 반환합니다.
    """
    query = """
    SELECT year, monthly_data, start_month, end_month
    FROM contribution_plans
    WHERE user_id = ?
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()

        plan = _default_yearly_plan()

        for row in rows:
            year_key = str(row["year"])
            if year_key not in plan:
                # YEARS 범위 밖의 데이터(과거 이관 등)도 보존
                plan[year_key] = {"start_month": 1, "end_month": 12, "monthly_data": _default_monthly_data()}

            raw_json = row["monthly_data"]
            try:
                monthly_data = json.loads(raw_json) if raw_json else _default_monthly_data()
            except (TypeError, json.JSONDecodeError):
                monthly_data = _default_monthly_data()

            # 기본 키 구조와 DB에서 로드된 monthly_data 병합 (새로 추가된 ISA 키 누락 방지)
            merged_monthly_data = _default_monthly_data()
            if isinstance(monthly_data, dict):
                merged_monthly_data.update(monthly_data)

            plan[year_key] = {
                "start_month": row["start_month"],
                "end_month": row["end_month"],
                "monthly_data": merged_monthly_data,
            }

        return plan
    except Exception as e:
        print(f"[DB ERROR] get_user_plan 실패 (user_id: {user_id}): {e}")
        return _default_yearly_plan()
    finally:
        if conn:
            conn.close()


def save_user_plan(user_id: int, plan_data: Dict[str, Any]) -> bool:
    """사용자의 연도별 연금 및 ISA 납입 플랜을 DB에 저장/업데이트(Upsert)합니다.

    plan_data 형태: {"2026": {"start_month":.., "end_month":.., "monthly_data": {...}}, "2027": {...}, ...}

    하위 호환: plan_data가 예전처럼 {"start_month":.., "end_month":.., "monthly_data": {...}} 단일 연도
    포맷으로 들어오면 2026년 데이터로 간주해 저장합니다.
    """
    # 레거시(단일 연도) 포맷 호환 처리
    if "monthly_data" in plan_data and "start_month" in plan_data:
        plan_data = {"2026": plan_data}

    query = """
    INSERT INTO contribution_plans (
        user_id, year, monthly_data, start_month, end_month, updated_at
    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(user_id, year) DO UPDATE SET
        monthly_data = excluded.monthly_data,
        start_month = excluded.start_month,
        end_month = excluded.end_month,
        updated_at = CURRENT_TIMESTAMP;
    """

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        for year_key, year_plan in plan_data.items():
            monthly_data = year_plan.get("monthly_data", DEFAULT_MONTHLY_DATA)

            # 모든 납입액을 Python int로 변환
            clean_monthly_data = {}
            for key, values in monthly_data.items():
                clean_monthly_data[key] = [int(v) if v is not None else 0 for v in values]

            monthly_json_str = json.dumps(clean_monthly_data, ensure_ascii=False)

            params = (
                user_id,
                int(year_key),
                monthly_json_str,
                year_plan.get("start_month", 1),
                year_plan.get("end_month", 12),
            )
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