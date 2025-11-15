from sqlalchemy import Column, String, DateTime, Integer, Numeric, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid


class PricingPlan(Base):
    __tablename__ = "pricing_plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String)
    api_calls_limit = Column(Integer)  # null = unlimited
    price_per_call = Column(Numeric(10, 4))
    monthly_fee = Column(Numeric(10, 2))
    features_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

