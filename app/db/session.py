from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite는 로컬 smoke test에서만 사용한다. FastAPI가 sync endpoint를
# thread pool에서 실행하므로 SQLite 연결의 thread 검사를 해제해야 한다.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

# pool_pre_ping은 빌려온 DB 연결이 살아 있는지 사용 전에 확인한다.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=connect_args,
)

# API 요청마다 이 팩토리로 독립적인 DB 세션을 만든다.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI endpoint에 DB 세션을 제공하고 요청 종료 후 닫는다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
