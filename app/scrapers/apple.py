from app.scrapers.base import BaseScraper, ScrapedProduct
from app.scrapers.exceptions import ParseError
from app.scrapers.json_ld import iter_json_ld, product_fields, schema_type_is


class AppleScraper(BaseScraper):
    """Apple UK 상품 페이지의 Product JSON-LD를 읽는다."""

    retailer = "Apple UK"
    supported_domains = ("apple.com",)

    def parse(self, html: str, url: str) -> ScrapedProduct:
        for node in iter_json_ld(html):
            if not schema_type_is(node, "Product"):
                continue

            title, price, currency = product_fields(node)
            return ScrapedProduct(
                retailer=self.retailer,
                title=title,
                price=price,
                currency=currency,
                url=url,
            )

        raise ParseError("Apple Product JSON-LD was not found")
