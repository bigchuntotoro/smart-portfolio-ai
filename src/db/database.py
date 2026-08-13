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
# DB 초기화
# =========================================================

def init_db():
    """테이블이 없으면 새로 생성합니다 (신규 스키마 기준, 마이그레이션 없음)."""
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
        # contribution_plans (연도별 월별 납입 계획 JSON, user_id + year 복합키)
        # ---------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS contribution_plans (
                user_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                monthly_data TEXT NOT NULL,
                start_month INTEGER NOT NULL DEFAULT 1,
                end_month INTEGER NOT NULL DEFAULT 12,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, year),
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


def reset_db():
    """기존 DB 파일을 완전히 삭제하고 새 스키마로 다시 생성합니다.

    주의: users, refresh_tokens, portfolios, contribution_plans 등
    모든 데이터가 영구적으로 삭제됩니다.
    """
    # WAL 모드 보조 파일(-wal, -shm)까지 함께 정리
    for suffix in ("", "-wal", "-shm"):
        target = Path(str(DB_PATH) + suffix)
        if target.exists():
            target.unlink()
            print(f"[DB RESET] {target.name} 삭제 완료")

    init_db()
    print("[DB RESET] 새 스키마로 데이터베이스를 재생성했습니다.")


if __name__ == "__main__":
    # 직접 실행하면 DB를 완전히 초기화합니다: python -m src.db.database
    confirm = input("정말로 기존 DB를 모두 삭제하고 새로 만드시겠습니까? (yes 입력): ")
    if confirm.strip().lower() == "yes":
        reset_db()
    else:
        print("취소되었습니다.")