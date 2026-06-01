import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

_engine: Engine | None = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    # EasyPanel/Heroku use postgres:// — SQLAlchemy needs postgresql+psycopg2://
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and "+psycopg2" not in url.split("://", 1)[0]:
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


def get_database_url() -> str | None:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return None
    return normalize_database_url(url)


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
        logger.warning("DATABASE_URL is not set — skipping database init")
        return

    try:
        from app import models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ready (orders, order_items, tracking_events)")
    except Exception as exc:
        # Keep API running so /health/db can surface the real connection error.
        logger.error("Database init failed: %s", exc)


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
