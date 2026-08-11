import sqlite3
from pathlib import Path


# =========================================================
# 프로젝트 루트
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

# =========================================================
# DB 디렉터리
# =========================================================

DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
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
        check_same_thread=False,
    )


# =========================================================
# DB 초기화
# =========================================================

def init_db():

    conn = get_connection()

    try:

        cursor = conn.cursor()

        # ---------------------------------------------
        # users
        # ---------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
            """
        )

        # ---------------------------------------------
        # portfolios
        # ---------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                age INTEGER NOT NULL,
                cash INTEGER DEFAULT 0,
                etf_amount INTEGER DEFAULT 0,
                bond_amount INTEGER DEFAULT 0,
                pension_amount INTEGER DEFAULT 0,
                monthly_etf INTEGER DEFAULT 0,
                monthly_bond INTEGER DEFAULT 0,
                monthly_pension INTEGER DEFAULT 0,
                selected_etf TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        conn.commit()

    finally:

        conn.close()
