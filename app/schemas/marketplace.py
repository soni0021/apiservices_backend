from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# Industry Schemas
class IndustryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon_url: Optional[str] = None


class IndustryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    icon_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Category Schemas
class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon_url: Optional[str] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    icon_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Service Schemas
class ServiceCreate(BaseModel):
    name: str
    slug: str
    category_id: Optional[str] = None
    description: Optional[str] = None
    endpoint_path: str
    request_schema: Optional[dict] = None
    response_schema: Optional[dict] = None
    price_per_call: Decimal = Decimal("1.0")
    industry_ids: Optional[List[str]] = None  # For many-to-many mapping


class ServiceResponse(BaseModel):
    id: str
    name: str
    slug: str
    category_id: Optional[str]
    description: Optional[str]
    endpoint_path: str
    request_schema: Optional[dict]
    response_schema: Optional[dict]
    price_per_call: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryResponse] = None
    industries: Optional[List[IndustryResponse]] = None

    class Config:
        from_attributes = True


# Subscription Schemas
class SubscriptionCreate(BaseModel):
    service_id: str
    credits_allocated: Decimal
    expires_at: Optional[datetime] = None


class SubscriptionResponse(BaseModel):
    id: str
    user_id: str
    service_id: str
    status: str
    credits_allocated: float
    credits_remaining: float
    started_at: datetime
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    service: Optional[ServiceResponse] = None

    class Config:
        from_attributes = True


# Transaction Schemas
class TransactionCreate(BaseModel):
    amount_paid: Decimal
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    amount_paid: float
    credits_purchased: float
    payment_method: Optional[str]
    payment_status: str
    transaction_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Credit Purchase Schema
class CreditPurchaseRequest(BaseModel):
    amount: Decimal  # Amount in rupees


class CreditPurchaseResponse(BaseModel):
    transaction_id: str
    amount_paid: float
    credits_purchased: float
    new_balance: float


# API Key Generation Schema
class APIKeyGenerateRequest(BaseModel):
    service_ids: Optional[List[str]] = None  # Optional: If empty/null, uses all services user has access to
    name: str
    # If service_ids contains "*", grants access to all services
    whitelist_urls: Optional[List[str]] = None  # Optional: Whitelist URLs for security


class AdminAPIKeyGenerateRequest(BaseModel):
    user_id: str  # Admin generates key for this user
    service_ids: List[str]  # Can be single, multiple, or ["*"] for all services
    name: str
    whitelist_urls: Optional[List[str]] = None  # Optional: Whitelist URLs for security


class APIKeyResponse(BaseModel):
    id: str
    service_id: Optional[str]  # Deprecated: for backward compatibility
    subscription_id: Optional[str]
    key_prefix: str
    full_key: Optional[str] = None  # Only shown once during creation
    name: str
    status: str
    allowed_services: Optional[List[str]] = None  # List of service IDs or ["*"]
    whitelist_urls: Optional[List[str]] = None  # Whitelist URLs
    last_used_at: Optional[datetime]
    created_at: datetime
    service: Optional[ServiceResponse] = None
    services: Optional[List[ServiceResponse]] = None  # Multiple services

    class Config:
        from_attributes = True

