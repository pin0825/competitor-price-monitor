# 모델을 한곳에서 import하면 SQLAlchemy가 모든 테이블을 metadata에 등록한다.
from app.models.listing import Listing
from app.models.price_observation import PriceObservation
from app.models.product import Product

__all__ = ["Listing", "PriceObservation", "Product"]
