from sqlalchemy import Column, String, DateTime, Date, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid


class FuelPriceData(Base):
    __tablename__ = "fuel_price_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    city = Column(String, nullable=True, index=True)  # null for state-level queries
    state = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    source = Column(String, nullable=True)
    fuel_prices = Column(JSON, nullable=True)  # Array of {fuel_type, price_per_litre/price_per_kg, currency, change_since_yesterday}
    data_source = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

