import sqlite3
from datetime import datetime, timezone

from src.db.database import get_connection


# =========================================================
# 회원가입
# =========================================================

def create_user(username, password_hash):

    if not username or not password_hash:
        return None

    conn = get_connection()

    try:
        cursor = conn.cursor()

        # 회원 INSERT (서비스 레이어에서 이미 해싱된 password_hash 저장)
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
# 사용자 조회 (username 기준)
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


# =========================================================
# 사용자 조회 (user_id 기준 - 신규 추가)
# =========================================================

def get_user_by_id(user_id):

    if not user_id:
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
            WHERE id = ?
            """,
            (
                user_id,
            ),
        )

        return cursor.fetchone()

    except Exception as e:

        print(
            f"[USER GET BY ID ERROR] {e}"
        )

        return None

    finally:

        conn.close()


# =========================================================
# Refresh Token 저장 / 갱신 (신규 추가)
# =========================================================

def save_refresh_token(user_id, refresh_token_hash, expires_at):

    if not user_id or not refresh_token_hash or not expires_at:
        return False

    conn = get_connection()

    try:

        cursor = conn.cursor()

        # ISO 포맷 문자열로 변환하여 DB 저장
        expires_at_str = (
            expires_at.isoformat()
            if isinstance(expires_at, datetime)
            else expires_at
        )

        # UPSERT: 동일 user_id가 존재하면 덮어쓰기
        cursor.execute(
            """
            INSERT INTO refresh_tokens (
                user_id,
                refresh_token_hash,
                expires_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                refresh_token_hash = excluded.refresh_token_hash,
                expires_at = excluded.expires_at,
                created_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                refresh_token_hash,
                expires_at_str,
            ),
        )

        conn.commit()

        print(
            f"[REFRESH TOKEN SAVE] "
            f"user_id={user_id}"
        )

        return True

    except Exception as e:

        conn.rollback()

        print(
            f"[REFRESH TOKEN SAVE ERROR] {e}"
        )

        return False

    finally:

        conn.close()


# =========================================================
# Refresh Token 조회 (신규 추가)
# =========================================================

def get_refresh_token_info(user_id):

    if not user_id:
        return None

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                refresh_token_hash,
                expires_at
            FROM refresh_tokens
            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        )

        row = cursor.fetchone()

        if not row:
            return None

        refresh_token_hash = row[0]
        expires_at_raw = row[1]

        # 문자열을 UTC timezone이 적용된 datetime 객체로 변환
        if isinstance(expires_at_raw, str):
            expires_at = datetime.fromisoformat(expires_at_raw)
        else:
            expires_at = expires_at_raw

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return refresh_token_hash, expires_at

    except Exception as e:

        print(
            f"[REFRESH TOKEN GET ERROR] {e}"
        )

        return None

    finally:

        conn.close()


# =========================================================
# Refresh Token 삭제 / 로그아웃 (신규 추가)
# =========================================================

def delete_refresh_token(user_id):

    if not user_id:
        return False

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM refresh_tokens
            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        )

        conn.commit()

        print(
            f"[REFRESH TOKEN DELETE] "
            f"user_id={user_id}"
        )

        return True

    except Exception as e:

        conn.rollback()

        print(
            f"[REFRESH TOKEN DELETE ERROR] {e}"
        )

        return False

    finally:

        conn.close()