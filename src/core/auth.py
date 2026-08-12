import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv

from src.db.user_dao import create_user, get_user

# DAO에 아래 함수들이 추가/구현되어 있어야 합니다:
# - save_refresh_token(user_id, refresh_token_hash, expires_at)
# - get_refresh_token_info(user_id)
# - delete_refresh_token(user_id)


# ==========================================
# 환경변수 로드
# ==========================================

load_dotenv()

# ==========================================
# JWT 및 토큰 설정
# ==========================================

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY가 .env에 설정되어 있지 않습니다."
    )

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Access Token: 짧은 만료시간 (기본 15분) -> Memory-Only 보관용
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)

# Refresh Token: 긴 만료시간 (기본 7일) -> DB 저장용
REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
)


# ==========================================
# 비밀번호 및 토큰 해시 함수
# ==========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증 함수 (72바이트 제한 처리)"""
    if not plain_password or not hashed_password:
        return False

    # 1. UTF-8 바이트 변환 후 최대 72바이트까지만 자름
    password_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")

    # 2. bcrypt 검증
    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        print(f"[AUTH ERROR] 비밀번호 검증 실패: {e}")
        return False

def hash_password(plain_password: str) -> str:
    """회원가입 시 비밀번호 해싱 함수 (72바이트 제한 처리)"""
    # UTF-8 바이트 변환 후 최대 72바이트 절단
    password_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def hash_token(token: str) -> str:
    """Refresh Token을 DB에 안전하게 저장하기 위한 bcrypt 해시"""
    return bcrypt.hashpw(
        token.encode("utf-8")[:72],
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_token_hash(token: str, token_hash: str) -> bool:
    """Refresh Token 일치 여부 검증"""
    return bcrypt.checkpw(
        token.encode("utf-8")[:72],
        token_hash.encode("utf-8")
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
# Access Token & Refresh Token 생성
# ==========================================

def create_access_token(user_id, username):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


def create_refresh_token():
    """예측 불가능한 무작위 Refresh Token 문자열 생성"""
    return secrets.token_urlsafe(48)


# ==========================================
# 로그인 (토큰 발급 및 DB 저장)
# ==========================================

def login(username, password):
    user = get_user(username)

    if not user:
        return None

    user_id = user[0]
    db_username = user[1]
    password_hash = user[2]

    # 비밀번호 검증
    if not verify_password(password, password_hash):
        return None

    # Access Token 발급 (Memory-Only 용도)
    access_token = create_access_token(user_id, db_username)

    # Refresh Token 발급 및 DB 저장
    refresh_token = create_refresh_token()
    refresh_token_hashed = hash_token(refresh_token)

    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    # DB에 기존 Refresh Token 덮어쓰기/저장
    # (DAO 구현 시 단일 기기 로그인 원칙 구현 가능)
    from src.db.user_dao import save_refresh_token
    save_refresh_token(user_id, refresh_token_hashed, expires_at)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,  # HTTP-Only Cookie로 응답 전달 권장
        "user_id": user_id,
        "username": db_username
    }


# ==========================================
# Refresh Token으로 Access Token 재발급
# ==========================================

def refresh_access_token(user_id, raw_refresh_token):
    """
    Refresh Token을 검증하고 새로운 Access Token을 발급합니다.
    """
    from src.db.user_dao import get_refresh_token_info, get_user_by_id

    # 1. DB에서 사용자의 저장된 Refresh Token 정보 조회
    # token_info 구조 예시: (hashed_token, expires_at)
    token_info = get_refresh_token_info(user_id)
    if not token_info:
        return None

    db_hashed_token, expires_at = token_info

    # 2. 만료 시간 검증
    if datetime.now(timezone.utc) > expires_at:
        return None

    # 3. 토큰 값 일치 여부 검증
    if not verify_token_hash(raw_refresh_token, db_hashed_token):
        return None

    # 4. 사용자 정보 조회 후 새로운 Access Token 생성
    user = get_user_by_id(user_id)
    if not user:
        return None

    db_username = user[1]
    new_access_token = create_access_token(user_id, db_username)

    return {
        "access_token": new_access_token
    }


# ==========================================
# 로그아웃 (Refresh Token 폐기)
# ==========================================

def logout(user_id):
    """DB에 저장된 Refresh Token을 삭제하여 세션을 종료합니다."""
    from src.db.user_dao import delete_refresh_token
    return delete_refresh_token(user_id)


# ==========================================
# Access Token 검증
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

        # Access Token 타입 확인 (Refresh Token 전달 방지)
        if payload.get("type") != "access":
            return None

        return payload

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None