from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """모든 SQLAlchemy ORM 모델이 상속하는 공통 기반 클래스다."""

    pass
