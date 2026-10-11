"""Database connection and session factory for SQLite."""
from __future__ import annotations
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

def now_utc(): return datetime.now(timezone.utc)

def _build_engine():
    url = os.getenv("DATABASE_URL", "sqlite:///./data/sentinel.db")
    kwargs = {"check_same_thread": False} if url.startswith("sqlite") else {}
    pool = {}
    if ":memory:" in url:
        from sqlalchemy.pool import StaticPool
        pool["poolclass"] = StaticPool
    eng = create_engine(url, connect_args=kwargs, **pool)
    if url.startswith("sqlite") and ":memory:" not in url:
        @event.listens_for(eng, "connect")
        def _set_pragmas(conn, _rec):
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    return eng

engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase): pass

def init_db() -> None:
    from backend.app.models import deck, evaluation, template, audit  # noqa: F401
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try: yield db
    finally: db.close()

@contextmanager
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db; db.commit()
    except Exception:
        db.rollback(); raise
    finally: db.close()
