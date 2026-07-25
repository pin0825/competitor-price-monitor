from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.price_alert_event import PriceAlertEvent
from app.models.price_alert_rule import PriceAlertRule
from app.models.price_observation import PriceObservation


def _create_event_if_triggered(
    db: Session,
    rule: PriceAlertRule,
    listing: Listing,
    observation: PriceObservation,
) -> PriceAlertEvent | None:
    """목표가 충족 여부와 중복을 검사한 뒤 이벤트를 추가한다."""
    if (
        not rule.is_active
        or rule.currency != listing.currency
        or observation.price > rule.target_price
    ):
        return None

    existing = db.scalar(
        select(PriceAlertEvent.id).where(
            PriceAlertEvent.rule_id == rule.id,
            PriceAlertEvent.observation_id == observation.id,
        )
    )
    if existing is not None:
        return None

    event = PriceAlertEvent(
        rule_id=rule.id,
        listing_id=listing.id,
        observation_id=observation.id,
        retailer=listing.retailer,
        observed_price=observation.price,
        target_price=rule.target_price,
        currency=listing.currency,
    )
    db.add(event)
    return event


def evaluate_price_alerts(
    db: Session,
    listing: Listing,
    observation: PriceObservation,
) -> list[PriceAlertEvent]:
    """새 가격 관측에 적용되는 모든 활성 규칙을 평가한다."""
    statement = select(PriceAlertRule).where(
        PriceAlertRule.product_id == listing.product_id,
        PriceAlertRule.is_active.is_(True),
        PriceAlertRule.currency == listing.currency,
        PriceAlertRule.target_price >= observation.price,
    )

    events = []
    for rule in db.scalars(statement):
        event = _create_event_if_triggered(db, rule, listing, observation)
        if event is not None:
            events.append(event)
    return events


def evaluate_rule_against_latest(
    db: Session,
    rule: PriceAlertRule,
) -> list[PriceAlertEvent]:
    """새 규칙을 각 판매처의 최신 저장 가격에 즉시 적용한다."""
    listings = db.scalars(
        select(Listing)
        .where(
            Listing.product_id == rule.product_id,
            Listing.is_active.is_(True),
        )
        .order_by(Listing.id)
    )

    events = []
    for listing in listings:
        latest = db.scalar(
            select(PriceObservation)
            .where(PriceObservation.listing_id == listing.id)
            .order_by(PriceObservation.observed_at.desc())
            .limit(1)
        )
        if latest is None:
            continue
        event = _create_event_if_triggered(db, rule, listing, latest)
        if event is not None:
            events.append(event)
    return events
