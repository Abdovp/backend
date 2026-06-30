import logging
import os
from urllib.parse import urlparse

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


def get_raw_database_url() -> str | None:
    url = os.getenv("DATABASE_URL", "").strip()
    return url or None


def get_database_url() -> str | None:
    url = get_raw_database_url()
    if not url:
        return None
    return normalize_database_url(url)


def get_database_target() -> dict:
    url = get_raw_database_url()
    if not url:
        return {"configured": False}

    parse_url = url.replace("postgres://", "postgresql://", 1)
    parsed = urlparse(parse_url)
    database = parsed.path.lstrip("/").split("?", 1)[0] if parsed.path else ""

    return {
        "configured": True,
        "host": parsed.hostname or "",
        "port": parsed.port or 5432,
        "database": database,
        "user": parsed.username or "",
    }


def get_engine() -> Engine | None:
    global _engine
    url = get_database_url()
    if not url:
        return None
    if _engine is None:
        _engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
        SessionLocal.configure(bind=_engine)
    return _engine


REQUIRED_TABLES = ("orders", "order_items", "tracking_events", "alembic_version")


def get_existing_tables() -> list[str]:
    engine = get_engine()
    if engine is None:
        return []

    from sqlalchemy import inspect

    return sorted(inspect(engine).get_table_names())


def run_migrations() -> None:
    engine = get_engine()
    if engine is None:
        logger.warning("DATABASE_URL is not set — skipping migrations")
        return

    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        database_url = get_database_url()
        if database_url:
            alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied (head)")
    except Exception as exc:
        logger.error("Alembic migration failed: %s", exc)


def init_db() -> None:
    engine = get_engine()
    if engine is None:
        logger.warning("DATABASE_URL is not set — skipping database init")
        return

    run_migrations()

    try:
        from app import models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        existing = get_existing_tables()
        missing = [name for name in REQUIRED_TABLES if name not in existing]
        if missing:
            logger.error("Missing database tables: %s", ", ".join(missing))
        else:
            logger.info("Database tables ready: %s", ", ".join(existing))
    except Exception as exc:
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
