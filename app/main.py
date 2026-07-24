from fastapi import FastAPI

from app.api.routes.collection import router as collection_router
from app.api.routes.prices import router as prices_router
from app.api.routes.products import router as products_router

# FastAPI 애플리케이션 객체다. Uvicorn이 app.main:app을 찾아 실행한다.
app = FastAPI(
    title="Competitor Price Monitor",
    version="0.1.0",
)

# products_router 안의 경로 앞에 /api/v1을 공통으로 붙인다.
app.include_router(products_router, prefix="/api/v1")
app.include_router(collection_router, prefix="/api/v1")
app.include_router(prices_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """서버 프로세스가 정상적으로 응답하는지 확인한다."""
    return {"status": "ok"}
