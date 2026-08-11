from src.db.database import get_connection


def get_portfolio(user_id):

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
            """,
            (user_id,)
        )

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "age": row[0],
            "cash": row[1],
            "etf_amount": row[2],
            "bond_amount": row[3],
            "pension_amount": row[4],
            "monthly_etf": row[5],
            "monthly_bond": row[6],
            "monthly_pension": row[7],
            "selected_etf": row[8],
        }

    finally:

        conn.close()


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

    conn = get_connection()

    try:

        cursor = conn.cursor()

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
            )
        )

        conn.commit()

        return True

    except Exception as e:

        print(
            f"포트폴리오 저장 오류: {e}"
        )

        conn.rollback()

        return False

    finally:

        conn.close()