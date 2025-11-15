from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class FuelPriceItem(BaseModel):
    fuel_type: str
    price_per_litre: Optional[float] = None
    price_per_kg: Optional[float] = None
    currency: str
    change_since_yesterday: float


class FuelPriceData(BaseModel):
    city: Optional[str] = None
    state: str
    date: str
    fuel_prices: List[FuelPriceItem]
    source: Optional[str] = None


class FuelPriceResponse(BaseModel):
    code: str
    message: str
    data: FuelPriceData

