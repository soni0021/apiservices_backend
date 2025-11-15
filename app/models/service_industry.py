from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class ServiceIndustry(Base):
    __tablename__ = "service_industries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    service_id = Column(String, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True)
    industry_id = Column(String, ForeignKey("industries.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    service = relationship("Service", back_populates="service_industries")
    industry = relationship("Industry", back_populates="service_industries")

