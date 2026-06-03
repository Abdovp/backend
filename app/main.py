from dotenv import load_dotenv
from sqlalchemy import func, select, text
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import get_settings
from app.api.admin import router as admin_router
from app.api.events import router as events_router
from app.api.orders import router as orders_router
from app.database import (
    SessionLocal,
    check_database_connection,
    get_database_target,
    get_engine,
    get_existing_tables,
    init_db,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.easypanel\.host",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"message": "Boya Shop API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    ok, detail = check_database_connection()
    tables = get_existing_tables() if ok else []
    missing = [name for name in ("orders", "order_items", "tracking_events", "alembic_version") if name not in tables]
    stats = {}
    migration = {}
    if ok and not missing:
        engine = get_engine()
        if engine:
            from app.models.order import Order, OrderItem
            from app.models.tracking import TrackingEvent

            with SessionLocal() as db:
                stats = {
                    "orders": db.scalar(select(func.count()).select_from(Order)) or 0,
                    "order_items": db.scalar(select(func.count()).select_from(OrderItem)) or 0,
                    "tracking_events": db.scalar(select(func.count()).select_from(TrackingEvent)) or 0,
                }
                try:
                    morocco_events = db.scalar(
                        select(func.count())
                        .select_from(TrackingEvent)
                        .where(TrackingEvent.country_code == "MA")
                    ) or 0
                    morocco_orders = db.scalar(
                        select(func.count()).select_from(Order).where(Order.country_code == "MA")
                    ) or 0
                    stats["morocco_tracking_events"] = morocco_events
                    stats["morocco_orders"] = morocco_orders
                except Exception:
                    stats["morocco_tracking_events"] = None
                    stats["morocco_orders"] = None

                try:
                    alembic_version = db.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
                    admin_columns = db.execute(
                        text(
                            """
                            SELECT COUNT(*) FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND (
                                (table_name = 'orders' AND column_name IN ('client_ip', 'country_code', 'admin_notes', 'updated_at'))
                                OR (table_name = 'tracking_events' AND column_name IN ('client_ip', 'country_code'))
                              )
                            """
                        )
                    ).scalar()
                    migration = {
                        "alembic_version": alembic_version,
                        "admin_columns_ready": admin_columns == 6,
                        "admin_columns_found": admin_columns,
                    }
                except Exception as exc:
                    migration = {"error": str(exc)}

    admin_configured = bool(
        settings.admin_username and settings.admin_password and settings.admin_jwt_secret
    )

    return {
        "status": "ok" if ok and not missing else "error",
        "database": detail,
        "target": get_database_target(),
        "tables": tables,
        "missing_tables": missing,
        "stats": stats,
        "migration": migration,
        "admin_configured": admin_configured,
    }


app.include_router(orders_router)
app.include_router(events_router)
app.include_router(admin_router)
