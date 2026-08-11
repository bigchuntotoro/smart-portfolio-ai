import sqlite3
import bcrypt

from src.db.database import get_connection


# =========================================================
# 회원가입
# =========================================================

def create_user(username, password):

    if not username or not password:
        return None

    conn = get_connection()

    try:

        cursor = conn.cursor()

        # -------------------------------------------------
        # 비밀번호 bcrypt 암호화
        # -------------------------------------------------

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        # -------------------------------------------------
        # 회원 INSERT
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO users (
                username,
                password_hash
            )
            VALUES (?, ?)
            """,
            (
                username.strip(),
                password_hash,
            ),
        )

        conn.commit()

        user_id = cursor.lastrowid

        print(
            f"[USER CREATE] "
            f"username={username}, "
            f"user_id={user_id}"
        )

        return user_id

    except sqlite3.IntegrityError as e:

        conn.rollback()

        print(
            f"[USER CREATE] "
            f"이미 존재하는 사용자: "
            f"{username} / {e}"
        )

        return None

    except Exception as e:

        conn.rollback()

        print(
            f"[USER CREATE ERROR] {e}"
        )

        return None

    finally:

        conn.close()


# =========================================================
# 사용자 조회
# =========================================================

def get_user(username):

    if not username:
        return None

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                username,
                password_hash
            FROM users
            WHERE username = ?
            """,
            (
                username.strip(),
            ),
        )

        return cursor.fetchone()

    except Exception as e:

        print(
            f"[USER GET ERROR] {e}"
        )

        return None

    finally:

        conn.close()
