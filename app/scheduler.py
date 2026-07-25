import asyncio
import logging

import httpx

from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("price-monitor-scheduler")


async def trigger_collection(client: httpx.AsyncClient) -> None:
    """인증 헤더와 함께 자동 수집 endpoint를 한 번 호출한다."""
    settings = get_settings()
    response = await client.post(
        f"{settings.scheduler_api_url}/api/v1/internal/"
        "scheduled-collection-runs",
        headers={"X-Collection-Key": settings.collection_api_key or ""},
    )
    response.raise_for_status()
    result = response.json()
    logger.info(
        "collection run=%s requested=%s created=%s unchanged=%s failed=%s",
        result["run_id"],
        result["requested"],
        result["created"],
        result["unchanged"],
        result["failed"],
    )


async def run_scheduler() -> None:
    """API 준비를 확인한 뒤 설정된 간격으로 자동 수집을 반복한다."""
    settings = get_settings()
    if not settings.collection_api_key:
        raise RuntimeError("COLLECTION_API_KEY must be configured")

    timeout = httpx.Timeout(90)
    async with httpx.AsyncClient(timeout=timeout) as client:
        if settings.scheduler_run_once:
            await trigger_collection(client)
            return

        if settings.scheduler_run_on_startup:
            try:
                await trigger_collection(client)
            except httpx.HTTPError:
                logger.exception("startup collection failed")

        logger.info(
            "scheduler ready interval_seconds=%s",
            settings.collection_interval_seconds,
        )
        while True:
            await asyncio.sleep(settings.collection_interval_seconds)
            try:
                await trigger_collection(client)
            except httpx.HTTPError:
                # 한 번 실패해도 프로세스를 종료하지 않고 다음 주기를 기다린다.
                logger.exception("scheduled collection failed")


if __name__ == "__main__":
    asyncio.run(run_scheduler())
