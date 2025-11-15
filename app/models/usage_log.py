from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class ApiUsageLog(Base):
    __tablename__ = "api_usage_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    api_key_id = Column(String, ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True, index=True)
    service_id = Column(String, ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True)
    subscription_id = Column(String, ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Request details
    endpoint_type = Column(String, nullable=False)  # rc, dl, challan, pan, gst, etc.
    request_params = Column(JSON)
    
    # Response details
    response_status = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=False)
    data_source = Column(String)  # db, api1, api2, api3
    
    # Credit tracking
    credits_deducted = Column(Numeric(10, 2), default=1.0, nullable=False)
    credits_before = Column(Numeric(10, 2), nullable=True)
    credits_after = Column(Numeric(10, 2), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", back_populates="usage_logs")
    api_key = relationship("ApiKey", back_populates="usage_logs")
    service = relationship("Service", back_populates="usage_logs")
    subscription = relationship("Subscription", back_populates="usage_logs")

