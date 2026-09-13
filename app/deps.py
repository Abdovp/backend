from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_engine
from app.services.auth import verify_admin_token


def get_db():
    if get_engine() is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_admin_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")

    return verify_admin_token(token.strip())
