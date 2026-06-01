import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

_engine: Engine | None = None


def get_database_url() -> str | None:
    url = os.getenv("DATABASE_URL", "").strip()
    return url or None


def get_engine() -> Engine | None:
    global _engine
    url = get_database_url()
    if not url:
        return None
    if _engine is None:
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


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
