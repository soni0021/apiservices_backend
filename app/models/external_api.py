from sqlalchemy import Column, String, DateTime, Integer, Boolean
from sqlalchemy.sql import func
from app.database import Base
import uuid


class ExternalApiConfig(Base):
    __tablename__ = "external_api_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    api_type = Column(String, nullable=False)  # rc, dl, challan
    base_url = Column(String, nullable=False)
    auth_type = Column(String)  # bearer, api_key, basic
    credentials_encrypted = Column(String)  # Encrypted credentials
    priority = Column(Integer, default=1)  # Lower number = higher priority
    circuit_breaker_threshold = Column(Integer, default=5)  # Failed attempts before disabling
    timeout_ms = Column(Integer, default=5000)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

