from app.scrapers.base import BaseScraper, ScrapedProduct
from app.scrapers.exceptions import ParseError
from app.scrapers.json_ld import iter_json_ld, product_fields, schema_type_is


class LaptopsDirectScraper(BaseScraper):
    """Laptops Direct @graph 내부의 Product JSON-LD를 읽는다."""

    retailer = "Laptops Direct"
    supported_domains = ("laptopsdirect.co.uk",)

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

        raise ParseError("Laptops Direct Product JSON-LD was not found")
