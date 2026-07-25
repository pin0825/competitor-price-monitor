from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 환경변수가 없을 때 로컬 개발에서 사용할 기본 PostgreSQL 주소다.
    database_url: str = (
        "postgresql+psycopg://price_monitor:price_monitor"
        "@localhost:5432/price_monitor"
    )
    # 자동 수집 전용 endpoint는 브라우저에 노출하지 않는 공유 키로 보호한다.
    collection_api_key: str | None = None
    scheduler_api_url: str = "http://api:8000"
    collection_interval_seconds: int = 21600
    scheduler_run_on_startup: bool = False
    scheduler_run_once: bool = False

    # .env 파일의 값을 읽되, 정의되지 않은 추가 환경변수는 무시한다.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """설정 객체를 한 번만 생성해 애플리케이션 전체에서 재사용한다."""
    return Settings()
