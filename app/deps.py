from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_engine


def get_db():
    if get_engine() is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
