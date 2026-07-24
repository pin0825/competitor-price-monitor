import json
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup

from app.scrapers.exceptions import ParseError


def iter_json_ld(html: str) -> Iterator[dict[str, Any]]:
    """HTML의 JSON-LD script를 읽고 내부 객체를 하나씩 반환한다."""
    soup = BeautifulSoup(html, "lxml")

    for script in soup.select('script[type="application/ld+json"]'):
        raw_json = script.string or script.get_text()
        if not raw_json.strip():
            continue

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            # 한 사이트에 잘못된 JSON-LD block이 있어도 다른 block은 계속 검사한다.
            continue

        yield from _walk_json_ld(data)


def _walk_json_ld(value: Any) -> Iterator[dict[str, Any]]:
    """@graph와 배열 안에 중첩된 JSON-LD 객체를 재귀적으로 순회한다."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json_ld(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json_ld(child)


def schema_type_is(node: dict[str, Any], expected_type: str) -> bool:
    """@type이 문자열 또는 배열인 두 경우를 모두 처리한다."""
    node_type = node.get("@type")
    if isinstance(node_type, str):
        return node_type == expected_type
    if isinstance(node_type, list):
        return expected_type in node_type
    return False


def first_offer(node: dict[str, Any]) -> dict[str, Any]:
    """Product의 offers가 객체 또는 배열인 경우 첫 가격 제안을 반환한다."""
    offers = node.get("offers")
    if isinstance(offers, dict):
        return offers
    if isinstance(offers, list) and offers and isinstance(offers[0], dict):
        return offers[0]
    raise ParseError("Product offer was not found in JSON-LD")


def parse_price(value: Any) -> Decimal:
    """JSON-LD 가격을 정확한 Decimal로 변환하고 양수인지 검증한다."""
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ParseError(f"Invalid price value: {value!r}") from exc

    if price <= 0:
        raise ParseError(f"Price must be greater than zero: {price}")

    return price.quantize(Decimal("0.01"))


def product_fields(node: dict[str, Any]) -> tuple[str, Decimal, str]:
    """Product JSON-LD에서 공통 상품 필드를 추출한다."""
    title = node.get("name")
    if not isinstance(title, str) or not title.strip():
        raise ParseError("Product name was not found in JSON-LD")

    offer = first_offer(node)
    currency = offer.get("priceCurrency")
    if not isinstance(currency, str) or len(currency) != 3:
        raise ParseError("Three-letter price currency was not found in JSON-LD")

    return title.strip(), parse_price(offer.get("price")), currency.upper()
