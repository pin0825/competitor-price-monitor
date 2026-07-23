from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# 테스트 전체가 같은 메모리 SQLite 연결을 사용하도록 StaticPool을 사용한다.
test_engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """각 테스트 전에 빈 schema를 만들고 끝나면 제거한다."""
    Base.metadata.create_all(bind=test_engine)
    with TestSessionLocal() as session:
        yield session
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """FastAPI의 실제 DB dependency를 테스트 세션으로 교체한다."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
