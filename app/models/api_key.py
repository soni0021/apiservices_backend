from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base
import uuid


class ApiKeyStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # service_id is now optional - can be null for multi-service keys
    service_id = Column(String, ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True)
    key_hash = Column(String, nullable=False, unique=True, index=True)
    key_prefix = Column(String(16), nullable=False)  # First 8-12 chars for display
    name = Column(String, nullable=False)
    status = Column(Enum(ApiKeyStatus), nullable=False, default=ApiKeyStatus.ACTIVE)
    
    # Multi-service access: stores list of service IDs this key can access
    # If null/empty, inherits from subscriptions; if ["*"], all services
    allowed_services = Column(JSON, nullable=True)  # ["service_id1", "service_id2"] or ["*"]
    
    # Security: Whitelist URLs - API will only respond to requests from these URLs
    # If null/empty, no restriction (allow all)
    whitelist_urls = Column(JSON, nullable=True)  # ["https://example.com", "https://app.example.com"]
    
    # Encrypted full key for retrieval (encrypted using JWT secret)
    encrypted_key = Column(String, nullable=True)
    
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="api_keys")
    service = relationship("Service", back_populates="api_keys")
    usage_logs = relationship("ApiUsageLog", back_populates="api_key", cascade="all, delete-orphan")

