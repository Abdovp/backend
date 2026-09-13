from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings

ALGORITHM = "HS256"


def get_admin_jwt_secret() -> str:
    settings = get_settings()
    return settings.admin_jwt_secret or "boya-admin-default-secret-change-me"


def create_admin_token(username: str) -> tuple[str, datetime]:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.admin_jwt_expire_hours)
    payload = {
        "sub": username,
        "exp": expires,
        "iat": datetime.now(timezone.utc),
        "role": "admin",
    }
    token = jwt.encode(payload, get_admin_jwt_secret(), algorithm=ALGORITHM)
    return token, expires


def verify_admin_token(token: str) -> str:
    try:
        payload = jwt.decode(token, get_admin_jwt_secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
    username = payload.get("sub")
    if not username or payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return username


def authenticate_admin(username: str, password: str) -> bool:
    settings = get_settings()
    if not settings.admin_username or not settings.admin_password:
        return False
    return username == settings.admin_username and password == settings.admin_password
