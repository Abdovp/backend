import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_engine: Engine | None = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_database_url() -> str | None:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return None
    # EasyPanel/Heroku use postgres:// — SQLAlchemy requires postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


def get_engine() -> Engine | None:
    global _engine
    url = get_database_url()
    if not url:
        return None
    if _engine is None:
        _engine = create_engine(url, pool_pre_ping=True)
        SessionLocal.configure(bind=_engine)
    return _engine


def init_db() -> None:
    engine = get_engine()
    if engine is None:
        return

    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def check_database_connection() -> tuple[bool, str]:
    engine = get_engine()
    if engine is None:
        return False, "DATABASE_URL is not set"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as exc:
        return False, str(exc)
