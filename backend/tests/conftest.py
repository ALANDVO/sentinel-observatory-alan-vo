"""Shared pytest fixtures for backend tests."""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set environment before importing anything from the app
os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["APP_ENV"] = "development"
os.environ["HOST"] = "testserver"

from backend.app.core.database import Base, get_db
from backend.app.main import create_app


@pytest.fixture(scope="session")
def engine():
    """In-memory SQLite engine shared across session."""
    from backend.app.core.database import engine as db_engine
    Base.metadata.create_all(bind=db_engine)
    return db_engine


@pytest.fixture(scope="function")
def db_session(engine):
    """Isolated database session per test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def client(engine):
    """FastAPI TestClient backed by in-memory DB."""
    app = create_app()
    Session = sessionmaker(bind=engine)

    def _override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
