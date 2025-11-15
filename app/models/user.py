from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Integer, Text, Date, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base
import uuid


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CLIENT = "client"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CLIENT)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    
    # New customer fields
    customer_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True, index=True)
    website_link = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    gst_number = Column(String, nullable=True)
    msme_certificate = Column(String, nullable=True)
    aadhar_number = Column(String, nullable=True)  # Should be encrypted in production
    pan_number = Column(String, nullable=True)
    birthday = Column(Date, nullable=True)
    about_me = Column(Text, nullable=True)
    
    # Credit tracking
    total_credits = Column(Numeric(10, 2), default=0, nullable=False)
    credits_used = Column(Numeric(10, 2), default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    api_tokens = relationship("ApiToken", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("ApiUsageLog", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class TokenType(str, enum.Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    token_type = Column(Enum(TokenType), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="api_tokens")

