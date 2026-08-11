import sqlite3
from pathlib import Path


# =========================================================
# 프로젝트 루트
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(
    exist_ok=True
)


# =========================================================
# SQLite DB
# =========================================================

DB_PATH = DATA_DIR / "users.db"


# =========================================================
# DB 연결
# =========================================================

def get_connection():

    return sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False
    )


# =========================================================
# DB 초기화
# =========================================================

def init_db():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )

    conn.commit()

    conn.close()
