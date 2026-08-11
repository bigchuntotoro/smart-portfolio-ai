import hashlib
from src.db.user_dao import create_user, get_user


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def signup(username, password):
    hashed = hash_password(password)
    return create_user(username, hashed)


def login(username, password):
    user = get_user(username)

    if not user:
        return False

    stored_password = user[2]
    return stored_password == hash_password(password)