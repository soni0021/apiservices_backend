from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models.user import User
from app.models.api_key import ApiKey, ApiKeyStatus
from app.models.usage_log import ApiUsageLog
from app.models.service import Service
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.transaction import Transaction, PaymentStatus
from app.models.category import Category
from app.models.industry import Industry
from app.models.service_industry import ServiceIndustry
from app.middleware.auth import get_current_active_user
from app.core.security import generate_api_key
from app.schemas.marketplace import (
    SubscriptionCreate, SubscriptionResponse,
    TransactionCreate, TransactionResponse,
    CreditPurchaseRequest, CreditPurchaseResponse,
    APIKeyGenerateRequest, APIKeyResponse,
    ServiceResponse
)
from app.websocket.manager import manager
from app.websocket.events import (
    create_credit_purchase_event,
    create_subscription_event,
    create_credit_balance_update_event
)
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from decimal import Decimal
import uuid

router = APIRouter()


# Schemas
class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    status: str
    last_used_at: Optional[datetime]
    created_at: datetime
    full_key: Optional[str] = None  # Only returned on creation


class UsageStats(BaseModel):
    total_calls: int
    calls_today: int
    calls_this_month: int
    by_endpoint: dict
    recent_calls: List[dict]


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


# Endpoints - Removed duplicate /api-keys endpoint
# Using list_api_keys_by_service below which includes service information


# Removed old POST /api-keys endpoint
# API keys must now be service-specific and require a subscription
# Use POST /api-keys/generate instead


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke an API key"""
    result = await db.execute(
        select(ApiKey).where(
            and_(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.status = ApiKeyStatus.REVOKED
    await db.commit()
    
    return {"message": "API key revoked successfully"}


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get usage statistics for current user"""
    # Total calls
    total_result = await db.execute(
        select(func.count(ApiUsageLog.id)).where(ApiUsageLog.user_id == current_user.id)
    )
    total_calls = total_result.scalar() or 0
    
    # Calls today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count(ApiUsageLog.id)).where(
            and_(
                ApiUsageLog.user_id == current_user.id,
                ApiUsageLog.created_at >= today_start
            )
        )
    )
    calls_today = today_result.scalar() or 0
    
    # Calls this month
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_result = await db.execute(
        select(func.count(ApiUsageLog.id)).where(
            and_(
                ApiUsageLog.user_id == current_user.id,
                ApiUsageLog.created_at >= month_start
            )
        )
    )
    calls_this_month = month_result.scalar() or 0
    
    # By endpoint
    endpoint_result = await db.execute(
        select(
            ApiUsageLog.endpoint_type,
            func.count(ApiUsageLog.id)
        ).where(ApiUsageLog.user_id == current_user.id)
        .group_by(ApiUsageLog.endpoint_type)
    )
    by_endpoint = {row[0]: row[1] for row in endpoint_result.all()}
    
    # Recent calls
    recent_result = await db.execute(
        select(ApiUsageLog)
        .where(ApiUsageLog.user_id == current_user.id)
        .order_by(ApiUsageLog.created_at.desc())
        .limit(10)
    )
    recent_logs = recent_result.scalars().all()
    recent_calls = [
        {
            "endpoint": log.endpoint_type,
            "status": log.response_status,
            "response_time_ms": log.response_time_ms,
            "data_source": log.data_source,
            "created_at": log.created_at.isoformat()
        }
        for log in recent_logs
    ]
    
    return UsageStats(
        total_calls=total_calls,
        calls_today=calls_today,
        calls_this_month=calls_this_month,
        by_endpoint=by_endpoint,
        recent_calls=recent_calls
    )


@router.get("/profile", response_model=dict)
async def get_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user profile"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "role": current_user.role.value,
        "status": current_user.status.value,
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat()
    }


@router.put("/profile")
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile"""
    if profile_data.full_name:
        current_user.full_name = profile_data.full_name
    if profile_data.phone:
        current_user.phone = profile_data.phone
    
    await db.commit()
    await db.refresh(current_user)
    
    return {"message": "Profile updated successfully"}


# Marketplace Endpoints
@router.get("/services", response_model=List[ServiceResponse])
async def browse_services(
    category_id: Optional[str] = None,
    industry_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Browse available services (filter by category/industry)"""
    query = select(Service).where(Service.is_active == True)
    
    if category_id:
        query = query.where(Service.category_id == category_id)
    
    if industry_id:
        # Join with service_industries
        query = query.join(ServiceIndustry).where(ServiceIndustry.industry_id == industry_id)
    
    result = await db.execute(
        query.options(selectinload(Service.category), selectinload(Service.service_industries))
    )
    services = result.scalars().all()
    
    return services


@router.get("/services/{service_id}", response_model=ServiceResponse)
async def get_service_details(
    service_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get service details"""
    result = await db.execute(
        select(Service)
        .where(Service.id == service_id, Service.is_active == True)
        .options(selectinload(Service.category), selectinload(Service.service_industries))
    )
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    
    return service


# Subscription creation removed - only admins can create subscriptions
# Clients can only view their subscriptions via GET /subscriptions


@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """View user's active subscriptions"""
    try:
        result = await db.execute(
            select(Subscription)
            .where(Subscription.user_id == current_user.id)
            .options(selectinload(Subscription.service))
            .order_by(Subscription.created_at.desc())
        )
        subscriptions = result.scalars().all()
        
        # Convert to response format
        return [
            SubscriptionResponse(
                id=sub.id,
                user_id=sub.user_id,
                service_id=sub.service_id,
                status=sub.status.value,
                credits_allocated=float(sub.credits_allocated),
                credits_remaining=float(sub.credits_remaining),
                started_at=sub.started_at,
                expires_at=sub.expires_at,
                created_at=sub.created_at,
                updated_at=sub.updated_at,
                service=ServiceResponse(
                    id=sub.service.id,
                    name=sub.service.name,
                    slug=sub.service.slug,
                    category_id=sub.service.category_id,
                    description=sub.service.description,
                    endpoint_path=sub.service.endpoint_path,
                    request_schema=sub.service.request_schema,
                    response_schema=sub.service.response_schema,
                    price_per_call=float(sub.service.price_per_call),
                    is_active=sub.service.is_active,
                    created_at=sub.service.created_at,
                    updated_at=sub.service.updated_at,
                    category=None,
                    industries=None
                ) if sub.service else None
            )
            for sub in subscriptions
        ]
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching subscriptions: {e}", exc_info=True)
        return []


@router.post("/api-keys/generate", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def generate_api_key_for_service(
    key_request: APIKeyGenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate API key for a subscribed service"""
    try:
        # Check if service exists
        result = await db.execute(select(Service).where(Service.id == key_request.service_id))
        service = result.scalar_one_or_none()
        
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        
        # Check if user has active subscription for this service
        sub_result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == current_user.id,
                Subscription.service_id == key_request.service_id,
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        subscription = sub_result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must have an active subscription for this service to generate an API key"
            )
        
        # Check if subscription has expired
        # Ensure both datetimes are timezone-aware for comparison
        if subscription.expires_at:
            now = datetime.now(timezone.utc)
            # Make expires_at timezone-aware if it's naive
            expires_at = subscription.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < now:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your subscription for this service has expired"
                )
        
        # Generate API key
        full_key, key_hash, key_prefix = generate_api_key("sk_live")
        
        # Create API key record
        api_key = ApiKey(
            user_id=current_user.id,
            service_id=key_request.service_id,
            subscription_id=subscription.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=key_request.name,
            status=ApiKeyStatus.ACTIVE
        )
        
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        
        # Reload service separately to ensure it's available
        service_result = await db.execute(select(Service).where(Service.id == key_request.service_id))
        loaded_service = service_result.scalar_one_or_none()
        
        # Build service response if available
        service_response = None
        if loaded_service:
            # Ensure updated_at has a value (use created_at if None)
            updated_at = loaded_service.updated_at if loaded_service.updated_at else loaded_service.created_at
            service_response = ServiceResponse(
                id=loaded_service.id,
                name=loaded_service.name,
                slug=loaded_service.slug,
                category_id=loaded_service.category_id,
                description=loaded_service.description,
                endpoint_path=loaded_service.endpoint_path,
                request_schema=loaded_service.request_schema,
                response_schema=loaded_service.response_schema,
                price_per_call=float(loaded_service.price_per_call),
                is_active=loaded_service.is_active,
                created_at=loaded_service.created_at,
                updated_at=updated_at,
                category=None,
                industries=None
            )
        
        return APIKeyResponse(
            id=api_key.id,
            service_id=api_key.service_id,
            subscription_id=api_key.subscription_id,
            key_prefix=api_key.key_prefix,
            full_key=full_key,  # Only shown once
            name=api_key.name,
            status=api_key.status.value,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            service=service_response
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating API key: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate API key: {str(e)}"
        )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys_by_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's API keys grouped by service"""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == current_user.id)
        .options(selectinload(ApiKey.service))
        .order_by(ApiKey.created_at.desc())
    )
    api_keys = result.scalars().all()
    
    return [
        APIKeyResponse(
            id=key.id,
            service_id=key.service_id or "",
            subscription_id=key.subscription_id,
            key_prefix=key.key_prefix,
            full_key=None,  # Never return full key in list
            name=key.name,
            status=key.status.value,
            last_used_at=key.last_used_at,
            created_at=key.created_at,
            service=ServiceResponse(
                id=key.service.id,
                name=key.service.name,
                slug=key.service.slug,
                category_id=key.service.category_id,
                description=key.service.description,
                endpoint_path=key.service.endpoint_path,
                request_schema=key.service.request_schema,
                response_schema=key.service.response_schema,
                price_per_call=float(key.service.price_per_call),
                is_active=key.service.is_active,
                created_at=key.service.created_at,
                updated_at=key.service.updated_at,
                category=None,
                industries=None
            ) if key.service else None
        )
        for key in api_keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke an API key"""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    
    api_key.status = ApiKeyStatus.REVOKED
    await db.commit()
    
    return {"message": "API key revoked successfully"}


@router.post("/credits/purchase", response_model=CreditPurchaseResponse, status_code=status.HTTP_201_CREATED)
async def purchase_credits(
    purchase_data: CreditPurchaseRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Buy credits (amount → credits conversion: ₹1000 = 200 credits)"""
    # Convert amount to credits (1:0.2 ratio)
    credits_purchased = purchase_data.amount * Decimal("0.2")
    
    # Create transaction
    transaction = Transaction(
        user_id=current_user.id,
        amount_paid=purchase_data.amount,
        credits_purchased=credits_purchased,
        payment_method="test",  # TODO: Integrate with payment gateway
        payment_status=PaymentStatus.COMPLETED,  # For now, auto-complete
        transaction_id=f"TXN-{uuid.uuid4().hex[:16].upper()}"
    )
    db.add(transaction)
    
    # Update user credits
    current_user.total_credits += credits_purchased
    
    await db.commit()
    await db.refresh(current_user)
    
    new_balance = float(current_user.total_credits - current_user.credits_used)
    
    # Broadcast event
    await manager.send_personal_message(
        create_credit_purchase_event(
            user_id=current_user.id,
            transaction_id=transaction.transaction_id,
            amount_paid=float(purchase_data.amount),
            credits_purchased=float(credits_purchased),
            new_balance=new_balance
        ),
        current_user.id
    )
    
    await manager.send_personal_message(
        create_credit_balance_update_event(
            user_id=current_user.id,
            total_credits=float(current_user.total_credits),
            credits_used=float(current_user.credits_used),
            credits_remaining=new_balance
        ),
        current_user.id
    )
    
    return CreditPurchaseResponse(
        transaction_id=transaction.transaction_id,
        amount_paid=float(purchase_data.amount),
        credits_purchased=float(credits_purchased),
        new_balance=new_balance
    )


@router.get("/credits/balance")
async def get_credit_balance(
    current_user: User = Depends(get_current_active_user)
):
    """Check credit balance"""
    credits_remaining = float(current_user.total_credits - current_user.credits_used)
    
    return {
        "total_credits": float(current_user.total_credits),
        "credits_used": float(current_user.credits_used),
        "credits_remaining": credits_remaining
    }


@router.get("/usage/history")
async def get_usage_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """API call history with credit deductions"""
    result = await db.execute(
        select(ApiUsageLog)
        .where(ApiUsageLog.user_id == current_user.id)
        .options(selectinload(ApiUsageLog.service))
        .order_by(ApiUsageLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()
    
    return [
        {
            "id": log.id,
            "service_id": log.service_id,
            "service_name": log.service.name if log.service else None,
            "endpoint_type": log.endpoint_type,
            "response_status": log.response_status,
            "response_time_ms": log.response_time_ms,
            "credits_deducted": float(log.credits_deducted),
            "credits_before": float(log.credits_before) if log.credits_before else None,
            "credits_after": float(log.credits_after) if log.credits_after else None,
            "data_source": log.data_source,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]

