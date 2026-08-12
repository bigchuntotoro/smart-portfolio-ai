import sqlite3
from pathlib import Path

# =========================================================
# 프로젝트 루트 및 DB 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "users.db"


# =========================================================
# DB 연결
# =========================================================

def get_connection():
    """SQLite DB 커넥션 생성"""
    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=30.0,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    # 매 연결 시 필요한 PRAGMA 설정
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")

    return conn


# =========================================================
# DB 초기화 및 마이그레이션
# =========================================================

def init_db():
    conn = None
    try:
        conn = get_connection()

        # WAL 모드는 DB 초기화 시점에 1회 설정
        conn.execute("PRAGMA journal_mode = WAL;")

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
        # refresh_tokens
        # ---------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                user_id INTEGER PRIMARY KEY,
                refresh_token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # ---------------------------------------------
        # contribution_plans (월별 납입 계획 JSON 포함)
        # ---------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS contribution_plans (
                user_id INTEGER PRIMARY KEY,
                monthly_data TEXT NOT NULL,
                start_month INTEGER NOT NULL DEFAULT 9,
                end_month INTEGER NOT NULL DEFAULT 12,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # 🔄 기존 DB 테이블이 이전 구조(p_sp500 컬럼 존재 등)일 경우 마이그레이션 처리
        cursor.execute("PRAGMA table_info(contribution_plans);")
        columns = [column[1] for column in cursor.fetchall()]

        if "monthly_data" not in columns:
            # 기존 구버전 테이블 삭제 후 신규 생성 (기존 단순 합계 구조와 호환 불가 대응)
            cursor.execute("DROP TABLE IF EXISTS contribution_plans;")
            cursor.execute(
                """
                CREATE TABLE contribution_plans (
                    user_id INTEGER PRIMARY KEY,
                    monthly_data TEXT NOT NULL,
                    start_month INTEGER NOT NULL DEFAULT 9,
                    end_month INTEGER NOT NULL DEFAULT 12,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )

        conn.commit()
        print("[DB INIT] 성공적으로 데이터베이스 테이블을 초기화했습니다.")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB INIT ERROR] {e}")

    finally:
        if conn:
            conn.close()