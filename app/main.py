from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import check_database_connection

load_dotenv()

app = FastAPI(title="Boya Shop API", version="1.0.0")

origins = [
    "https://boya-shop.online",
    "https://www.boya-shop.online",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Boya Shop API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    ok, detail = check_database_connection()
    return {"status": "ok" if ok else "error", "database": detail}
