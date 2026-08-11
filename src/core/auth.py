import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv

from src.db.user_dao import create_user, get_user


# ==========================================
# 환경변수 로드
# ==========================================

load_dotenv()


# ==========================================
# JWT 설정
# ==========================================

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY가 .env에 설정되어 있지 않습니다."
    )


JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

JWT_EXPIRE_MINUTES = int(
    os.getenv(
        "JWT_EXPIRE_MINUTES",
        "60"
    )
)


# ==========================================
# 비밀번호 해시
# ==========================================

def hash_password(password):
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


# ==========================================
# 비밀번호 검증
# ==========================================

def verify_password(password, password_hash):
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )


# ==========================================
# 회원가입
# ==========================================

def signup(username, password):

    if not username or not password:
        return False

    password_hash = hash_password(password)

    return create_user(
        username,
        password_hash
    )


# ==========================================
# JWT 발급
# ==========================================

def create_access_token(user_id, username):

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + timedelta(
            minutes=JWT_EXPIRE_MINUTES
        )
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

    return token


# ==========================================
# 로그인
# ==========================================

def login(username, password):

    user = get_user(username)

    if not user:
        return None

    user_id = user[0]
    db_username = user[1]
    password_hash = user[2]

    # 비밀번호 검증
    if not verify_password(
        password,
        password_hash
    ):
        return None

    # JWT 발급
    token = create_access_token(
        user_id,
        db_username
    )

    return {
        "access_token": token,
        "user_id": user_id,
        "username": db_username
    }


# ==========================================
# JWT 검증
# ==========================================

def verify_token(token):

    if not token:
        return None

    try:

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        return payload

    except jwt.ExpiredSignatureError:

        return None

    except jwt.InvalidTokenError:

        return None
