from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.alerts import router as alerts_router
from app.api.routes.collection import router as collection_router
from app.api.routes.listings import router as listings_router
from app.api.routes.prices import router as prices_router
from app.api.routes.products import router as products_router

# FastAPI 애플리케이션 객체다. Uvicorn이 app.main:app을 찾아 실행한다.
app = FastAPI(
    title="Competitor Price Monitor",
    version="0.1.0",
)

# 프론트엔드 파일은 FastAPI와 같은 컨테이너에서 제공한다.
static_directory = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_directory), name="static")

# products_router 안의 경로 앞에 /api/v1을 공통으로 붙인다.
app.include_router(products_router, prefix="/api/v1")
app.include_router(listings_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(collection_router, prefix="/api/v1")
app.include_router(prices_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """가격 모니터링 대시보드 화면을 반환한다."""
    return FileResponse(static_directory / "index.html")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """서버 프로세스가 정상적으로 응답하는지 확인한다."""
    return {"status": "ok"}
