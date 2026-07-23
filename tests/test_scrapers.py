import json
from decimal import Decimal

import pytest

from app.scrapers.apple import AppleScraper
from app.scrapers.exceptions import ParseError, UnsupportedUrlError
from app.scrapers.john_lewis import JohnLewisScraper
from app.scrapers.json_ld import parse_price
from app.scrapers.laptops_direct import LaptopsDirectScraper
from app.scrapers.registry import get_scraper_for_url


def _html_with_json_ld(data: dict) -> str:
    return (
        "<html><head>"
        '<script type="application/ld+json">'
        f"{json.dumps(data)}"
        "</script>"
        "</head></html>"
    )


def test_apple_scraper_parses_product_json_ld() -> None:
    url = (
        "https://www.apple.com/uk/shop/buy-iphone/iphone-17/"
        "6.3-inch-display-256gb-black"
    )
    html = _html_with_json_ld(
        {
            "@type": "Product",
            "name": "iPhone 17 256GB Black",
            "offers": [
                {
                    "@type": "Offer",
                    "price": 799,
                    "priceCurrency": "GBP",
                }
            ],
        }
    )

    result = AppleScraper().parse(html, url)

    assert result.title == "iPhone 17 256GB Black"
    assert result.price == Decimal("799.00")
    assert result.currency == "GBP"


def test_john_lewis_scraper_selects_variant_matching_url() -> None:
    black_url = (
        "https://www.johnlewis.com/apple-iphone-17-256gb/"
        "black/p114322975"
    )
    html = _html_with_json_ld(
        {
            "@type": "ProductGroup",
            "hasVariant": [
                {
                    "@type": "Product",
                    "name": "iPhone 17 256GB White",
                    "url": black_url.replace("black", "white"),
                    "offers": {"price": "799.00", "priceCurrency": "GBP"},
                },
                {
                    "@type": "Product",
                    "name": "iPhone 17 256GB Black",
                    "url": black_url,
                    "offers": {"price": "789.00", "priceCurrency": "GBP"},
                },
            ],
        }
    )

    result = JohnLewisScraper().parse(html, f"{black_url}?tracking=test")

    assert result.title == "iPhone 17 256GB Black"
    assert result.price == Decimal("789.00")


def test_laptops_direct_scraper_reads_product_inside_graph() -> None:
    url = "https://www.laptopsdirect.co.uk/iphone-17/version.asp"
    html = _html_with_json_ld(
        {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "Organization", "name": "Laptops Direct"},
                {
                    "@type": "Product",
                    "name": "Apple iPhone 17 Black 256GB",
                    "offers": {
                        "@type": "Offer",
                        "price": 749,
                        "priceCurrency": "GBP",
                    },
                },
            ],
        }
    )

    result = LaptopsDirectScraper().parse(html, url)

    assert result.price == Decimal("749.00")
    assert result.retailer == "Laptops Direct"


def test_price_validation_rejects_non_positive_value() -> None:
    with pytest.raises(ParseError):
        parse_price("0")


def test_registry_rejects_unsupported_domain() -> None:
    with pytest.raises(UnsupportedUrlError):
        get_scraper_for_url("https://example.com/product/1")
