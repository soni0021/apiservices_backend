from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class Service(Base):
    __tablename__ = "services"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    category_id = Column(String, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(String, nullable=True)
    endpoint_path = Column(String, nullable=False)
    request_schema = Column(JSON, nullable=True)
    response_schema = Column(JSON, nullable=True)
    price_per_call = Column(Numeric(10, 2), default=1.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    category = relationship("Category", back_populates="services")
    service_industries = relationship("ServiceIndustry", back_populates="service", cascade="all, delete-orphan")
    user_access = relationship("UserServiceAccess", back_populates="service", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="service")
    usage_logs = relationship("ApiUsageLog", back_populates="service")

