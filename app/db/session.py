from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}

# Serverless / free PostgreSQL (for example Neon) closes idle connections. pool_pre_ping tests a
# connection before using it and pool_recycle retires old ones, so the first request after a pause
# does not fail with "SSL connection has been closed unexpectedly". The small pool respects the
# connection limits of free plans.
_engine_options = {} if _is_sqlite else {
    "pool_pre_ping": True,
    "pool_recycle": 240,
    "pool_size": 3,
    "max_overflow": 2,
}

engine = create_engine(settings.database_url, connect_args=connect_args, **_engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
