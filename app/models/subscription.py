from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base
import uuid


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(String, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    credits_allocated = Column(Numeric(10, 2), default=0, nullable=False)
    credits_remaining = Column(Numeric(10, 2), default=0, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    service = relationship("Service", back_populates="subscriptions")
    api_keys = relationship("ApiKey", back_populates="subscription")
    usage_logs = relationship("ApiUsageLog", back_populates="subscription")

