from src.db.database import get_connection


# =========================================================
# 회원별 포트폴리오 조회
# =========================================================

def get_portfolio(user_id):
    """
    로그인한 회원의 포트폴리오를 조회한다.

    Parameters
    ----------
    user_id : int
        로그인한 회원 ID

    Returns
    -------
    dict | None
    """

    if user_id is None:
        return None

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                age,
                cash,
                etf_amount,
                bond_amount,
                pension_amount,
                monthly_etf,
                monthly_bond,
                monthly_pension,
                selected_etf
            FROM portfolios
            WHERE user_id = ?
            LIMIT 1
            """,
            (user_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "age": int(row[0] or 0),
            "cash": int(row[1] or 0),
            "etf_amount": int(row[2] or 0),
            "bond_amount": int(row[3] or 0),
            "pension_amount": int(row[4] or 0),
            "monthly_etf": int(row[5] or 0),
            "monthly_bond": int(row[6] or 0),
            "monthly_pension": int(row[7] or 0),
            "selected_etf": row[8] or "",
        }

    except Exception as e:
        print(f"[PORTFOLIO LOAD ERROR] {e}")
        return None

    finally:
        conn.close()


# =========================================================
# 회원별 포트폴리오 저장
# =========================================================

def save_portfolio(
    user_id,
    age,
    cash,
    etf_amount,
    bond_amount,
    pension_amount,
    monthly_etf,
    monthly_bond,
    monthly_pension,
    selected_etf,
):
    """
    회원별 포트폴리오를 저장한다.

    이미 존재하는 user_id라면 UPDATE,
    없으면 INSERT 한다.
    """

    if user_id is None:
        return False

    try:
        user_id = int(user_id)
        age = int(age)
        cash = int(cash)
        etf_amount = int(etf_amount)
        bond_amount = int(bond_amount)
        pension_amount = int(pension_amount)
        monthly_etf = int(monthly_etf)
        monthly_bond = int(monthly_bond)
        monthly_pension = int(monthly_pension)
    except (TypeError, ValueError):
        return False

    conn = get_connection()

    try:
        cursor = conn.cursor()

        # =================================================
        # 1. users 테이블에 회원 존재 여부 확인
        # =================================================

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
            LIMIT 1
            """,
            (user_id,),
        )

        user = cursor.fetchone()

        if user is None:
            print(
                f"[PORTFOLIO SAVE ERROR] "
                f"존재하지 않는 user_id={user_id}"
            )
            return False

        # =================================================
        # 2. 포트폴리오 저장
        # =================================================

        cursor.execute(
            """
            INSERT INTO portfolios (
                user_id,
                age,
                cash,
                etf_amount,
                bond_amount,
                pension_amount,
                monthly_etf,
                monthly_bond,
                monthly_pension,
                selected_etf
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                age = excluded.age,
                cash = excluded.cash,
                etf_amount = excluded.etf_amount,
                bond_amount = excluded.bond_amount,
                pension_amount = excluded.pension_amount,
                monthly_etf = excluded.monthly_etf,
                monthly_bond = excluded.monthly_bond,
                monthly_pension = excluded.monthly_pension,
                selected_etf = excluded.selected_etf,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                age,
                cash,
                etf_amount,
                bond_amount,
                pension_amount,
                monthly_etf,
                monthly_bond,
                monthly_pension,
                selected_etf,
            ),
        )

        conn.commit()

        print(
            f"[PORTFOLIO SAVE] "
            f"user_id={user_id}, "
            f"selected_etf={selected_etf}"
        )

        return True

    except Exception as e:

        conn.rollback()

        print(
            f"[PORTFOLIO SAVE ERROR] {e}"
        )

        return False

    finally:
        conn.close()


# =========================================================
# 회원별 포트폴리오 삭제
# =========================================================

def delete_portfolio(user_id):
    """
    회원의 포트폴리오를 삭제한다.
    """

    if user_id is None:
        return False

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return False

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM portfolios
            WHERE user_id = ?
            """,
            (user_id,),
        )

        conn.commit()

        return True

    except Exception as e:

        conn.rollback()

        print(
            f"[PORTFOLIO DELETE ERROR] {e}"
        )

        return False

    finally:
        conn.close()