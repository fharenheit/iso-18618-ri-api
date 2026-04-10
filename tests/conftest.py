import shutil

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.config import STORAGE_DIR
from app.database import get_db
from app.main import app
from app.models.db_models import Base

TEST_DB_URL = "postgresql://ids_user:ids_pass@localhost:5432/ids_api_test"

_engine = create_engine(TEST_DB_URL)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables in test database once per session."""
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)
    yield
    _engine.dispose()


@pytest.fixture()
def db_session():
    """Provide a DB session that uses savepoints so service commits are isolated."""
    connection = _engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """FastAPI test client with DB session override."""
    from fastapi.testclient import TestClient

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def cleanup_storage():
    """Clean storage directory for tests."""
    existing = set(STORAGE_DIR.iterdir()) if STORAGE_DIR.exists() else set()
    yield
    if STORAGE_DIR.exists():
        for d in STORAGE_DIR.iterdir():
            if d not in existing and d.is_dir():
                shutil.rmtree(d)
