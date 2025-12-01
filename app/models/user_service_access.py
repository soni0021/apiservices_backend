from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class UserServiceAccess(Base):
    """Tracks which services a user has access to (granted by admin)"""
    __tablename__ = "user_service_access"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(String, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Admin who granted access
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="service_access")
    service = relationship("Service", back_populates="user_access")
    granted_by_user = relationship("User", foreign_keys=[granted_by])

