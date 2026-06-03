from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_engine
from app.services.auth import verify_admin_token

_bearer = HTTPBearer(auto_error=False)


def get_db():
    if get_engine() is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_admin_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")
    return verify_admin_token(credentials.credentials)
