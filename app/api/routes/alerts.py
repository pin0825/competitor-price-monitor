from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.price_alert_event import PriceAlertEvent
from app.models.price_alert_rule import PriceAlertRule
from app.models.product import Product
from app.schemas.alert import (
    AlertEventRead,
    AlertRuleCreate,
    AlertRuleRead,
    AlertRuleUpdate,
)
from app.services.alerts import evaluate_rule_against_latest

router = APIRouter(tags=["alerts"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/products/{product_id}/alert-rules",
    response_model=AlertRuleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_alert_rule(
    product_id: int,
    payload: AlertRuleCreate,
    db: DbSession,
) -> PriceAlertRule:
    """목표가 규칙을 만들고 이미 저장된 최신 가격에도 즉시 적용한다."""
    if db.get(Product, product_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    rule = PriceAlertRule(product_id=product_id, **payload.model_dump())
    db.add(rule)
    db.flush()
    evaluate_rule_against_latest(db, rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get(
    "/products/{product_id}/alert-rules",
    response_model=list[AlertRuleRead],
)
def list_alert_rules(
    product_id: int,
    db: DbSession,
) -> list[PriceAlertRule]:
    """상품에 설정된 목표가 규칙을 최신순으로 반환한다."""
    if db.get(Product, product_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    statement = (
        select(PriceAlertRule)
        .where(PriceAlertRule.product_id == product_id)
        .order_by(PriceAlertRule.created_at.desc(), PriceAlertRule.id.desc())
    )
    return list(db.scalars(statement).all())


@router.patch(
    "/alert-rules/{rule_id}",
    response_model=AlertRuleRead,
)
def update_alert_rule(
    rule_id: int,
    payload: AlertRuleUpdate,
    db: DbSession,
) -> PriceAlertRule:
    """목표가와 활성 상태를 수정하고 활성 규칙을 다시 평가한다."""
    rule = db.get(PriceAlertRule, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    if rule.is_active:
        evaluate_rule_against_latest(db, rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/alert-events", response_model=list[AlertEventRead])
def list_alert_events(
    db: DbSession,
    product_id: int | None = None,
    acknowledged: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PriceAlertEvent]:
    """필터 가능한 가격 알림 이벤트를 최신순으로 반환한다."""
    statement = select(PriceAlertEvent).join(PriceAlertRule)
    if product_id is not None:
        statement = statement.where(PriceAlertRule.product_id == product_id)
    if acknowledged is True:
        statement = statement.where(
            PriceAlertEvent.acknowledged_at.is_not(None)
        )
    elif acknowledged is False:
        statement = statement.where(
            PriceAlertEvent.acknowledged_at.is_(None)
        )
    statement = statement.order_by(
        PriceAlertEvent.triggered_at.desc(),
        PriceAlertEvent.id.desc(),
    ).limit(limit)
    return list(db.scalars(statement).all())


@router.patch(
    "/alert-events/{event_id}/acknowledge",
    response_model=AlertEventRead,
)
def acknowledge_alert_event(
    event_id: int,
    db: DbSession,
) -> PriceAlertEvent:
    """사용자가 확인한 이벤트에 확인 시각을 기록한다."""
    event = db.get(PriceAlertEvent, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert event not found",
        )
    if event.acknowledged_at is None:
        event.acknowledged_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(event)
    return event
