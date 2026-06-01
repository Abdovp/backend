from dotenv import load_dotenv
from sqlalchemy import func, select
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.events import router as events_router
from app.api.orders import router as orders_router
from app.database import SessionLocal, check_database_connection, get_engine, init_db

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Boya Shop API", version="1.0.0")

origins = [
    "https://boya-shop.online",
    "https://www.boya-shop.online",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    stats = {}
    if ok:
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
    return {"status": "ok" if ok else "error", "database": detail, "stats": stats}


app.include_router(orders_router)
app.include_router(events_router)
