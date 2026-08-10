import sqlite3

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS portfolio (
    username TEXT,
    cash INTEGER,
    etf_amount INTEGER,
    bond_amount INTEGER,
    pension_amount INTEGER,
    PRIMARY KEY (username)
)
""")

conn.commit()
conn.close()

print("✅ DB 생성 완료")