import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .api.v1 import accounts, audit, auth, documents, library, onlyoffice, pitfalls, stats
from .core.config import CORS_ORIGINS
from .core.exceptions import register_exception_handlers
from .db import Base, SessionLocal, engine
from .middleware.request_log import RequestLogMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware
from .seed import seed_if_empty

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title="装修共享网站", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLogMiddleware)

register_exception_handlers(app)

for r in (auth.router, stats.router, documents.router, onlyoffice.router,
          library.router, pitfalls.router, accounts.router, audit.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/api/health")
def health():
    db_ok = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_ok = False
    return {"status": "ok", "database": "up" if db_ok else "down", "version": "2.0.0"}
