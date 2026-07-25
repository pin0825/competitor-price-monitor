# 모델을 한곳에서 import하면 SQLAlchemy가 모든 테이블을 metadata에 등록한다.
from app.models.collection_attempt import CollectionAttempt
from app.models.collection_run import CollectionRun
from app.models.listing import Listing
from app.models.price_alert_event import PriceAlertEvent
from app.models.price_alert_rule import PriceAlertRule
from app.models.price_observation import PriceObservation
from app.models.product import Product

__all__ = [
    "CollectionAttempt",
    "CollectionRun",
    "Listing",
    "PriceAlertEvent",
    "PriceAlertRule",
    "PriceObservation",
    "Product",
]
