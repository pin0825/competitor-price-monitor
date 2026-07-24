from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlparse

import httpx

from app.scrapers.exceptions import FetchError, UnsupportedUrlError


@dataclass(frozen=True)
class ScrapedProduct:
    """스크래퍼가 사이트와 관계없이 동일한 형태로 반환하는 결과다."""

    retailer: str
    title: str
    price: Decimal
    currency: str
    url: str


class BaseScraper(ABC):
    """모든 사이트별 scraper가 따라야 하는 공통 인터페이스다."""

    retailer: str
    supported_domains: tuple[str, ...]

    def supports(self, url: str) -> bool:
        """URL의 hostname이 이 scraper가 담당하는 도메인인지 확인한다."""
        hostname = (urlparse(url).hostname or "").lower()
        return any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in self.supported_domains
        )

    async def scrape(
        self,
        url: str,
        client: httpx.AsyncClient,
    ) -> ScrapedProduct:
        """페이지를 비동기로 다운로드한 뒤 사이트별 파서에 전달한다."""
        if not self.supports(url):
            raise UnsupportedUrlError(
                f"{self.retailer} scraper does not support URL: {url}"
            )

        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FetchError(
                f"Failed to fetch {self.retailer} page: {url}"
            ) from exc

        return self.parse(response.text, str(response.url))

    @abstractmethod
    def parse(self, html: str, url: str) -> ScrapedProduct:
        """사이트 HTML에서 상품명·가격·통화를 추출한다."""
