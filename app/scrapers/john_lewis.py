from urllib.parse import urlsplit, urlunsplit

from app.scrapers.base import BaseScraper, ScrapedProduct
from app.scrapers.exceptions import ParseError
from app.scrapers.json_ld import iter_json_ld, product_fields, schema_type_is


def _without_query_or_fragment(url: str) -> str:
    """추적용 query string을 제외하고 실제 상품 URL 부분만 비교한다."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


class JohnLewisScraper(BaseScraper):
    """John Lewis ProductGroup에서 현재 URL과 같은 색상 variant를 선택한다."""

    retailer = "John Lewis"
    supported_domains = ("johnlewis.com",)

    def parse(self, html: str, url: str) -> ScrapedProduct:
        requested_url = _without_query_or_fragment(url)

        for node in iter_json_ld(html):
            if not schema_type_is(node, "Product"):
                continue

            variant_url = node.get("url")
            if not isinstance(variant_url, str):
                continue
            if _without_query_or_fragment(variant_url) != requested_url:
                continue

            title, price, currency = product_fields(node)
            return ScrapedProduct(
                retailer=self.retailer,
                title=title,
                price=price,
                currency=currency,
                url=url,
            )

        raise ParseError("Matching John Lewis product variant was not found")
