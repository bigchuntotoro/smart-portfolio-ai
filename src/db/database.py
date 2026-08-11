import os
import sqlite3


# ==========================================
# 프로젝트 기준 경로
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)


# ==========================================
# DB 경로
# ==========================================

DB_DIR = os.path.join(
    BASE_DIR,
    "data"
)

DB_PATH = os.path.join(
    DB_DIR,
    "users.db"
)


# ==========================================
# DB 연결
# ==========================================

def get_connection():

    # data 폴더가 없으면 자동 생성
    os.makedirs(
        DB_DIR,
        exist_ok=True
    )

    return sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )


# ==========================================
# DB 초기화
# ==========================================

def init_db():

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)

        conn.commit()

    finally:

        conn.close()
