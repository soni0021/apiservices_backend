from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models.user import User
from app.models.api_key import ApiKey, ApiKeyStatus
from app.models.usage_log import ApiUsageLog
from app.models.service import Service
from app.models.user_service_access import UserServiceAccess
from app.models.transaction import Transaction, PaymentStatus
from app.models.category import Category
from app.models.industry import Industry
from app.models.service_industry import ServiceIndustry
from app.middleware.auth import get_current_active_user
from app.core.security import generate_api_key
from app.schemas.marketplace import (
    TransactionCreate, TransactionResponse,
    CreditPurchaseRequest, CreditPurchaseResponse,
    APIKeyGenerateRequest, APIKeyResponse,
    ServiceResponse
)
from app.websocket.manager import manager
from app.websocket.events import (
    create_credit_purchase_event,
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
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key permanently from database"""
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
    
    # Actually delete from database
    await db.delete(api_key)
    await db.commit()
    
    return {"message": "API key deleted successfully"}


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


# Subscriptions removed - users now have direct service access managed by admin

@router.get("/service-access", response_model=List[ServiceResponse])
async def get_user_service_access(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of services the current user has access to"""
    # Get all service access records for this user
    access_result = await db.execute(
        select(UserServiceAccess).where(UserServiceAccess.user_id == current_user.id)
    )
    access_records = access_result.scalars().all()
    
    # Get service IDs
    service_ids = [access.service_id for access in access_records]
    
    if not service_ids:
        return []
    
    # Fetch services
    services_result = await db.execute(
        select(Service)
        .where(Service.id.in_(service_ids))
        .where(Service.is_active == True)
        .options(selectinload(Service.category))
    )
    services = services_result.scalars().all()
    
    return [
        ServiceResponse(
            id=svc.id,
            name=svc.name,
            slug=svc.slug,
            category_id=svc.category_id,
            description=svc.description,
            endpoint_path=svc.endpoint_path,
            request_schema=svc.request_schema,
            response_schema=svc.response_schema,
            price_per_call=float(svc.price_per_call),
            is_active=svc.is_active,
            created_at=svc.created_at,
            updated_at=svc.updated_at if svc.updated_at else svc.created_at,
            category=None,
            industries=None
        )
        for svc in services
    ]


@router.post("/api-keys/generate", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def generate_api_key_for_client(
    key_data: APIKeyGenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Client generates their own API key for services they have access to"""
    from app.core.security import generate_api_key, encrypt_api_key
    
    # If service_ids is not provided or empty, automatically use all services user has access to
    if not key_data.service_ids or len(key_data.service_ids) == 0:
        # Get all services user has access to
        access_result = await db.execute(
            select(UserServiceAccess).where(
                UserServiceAccess.user_id == current_user.id
            )
        )
        access_records = access_result.scalars().all()
        
        if not access_records:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to any services. Contact admin to grant access."
            )
        
        # Extract service IDs from access records
        service_ids = [access.service_id for access in access_records]
    else:
        # Validate that user has access to all requested services
        service_ids = key_data.service_ids
        for service_id in service_ids:
            access_result = await db.execute(
                select(UserServiceAccess).where(
                    UserServiceAccess.user_id == current_user.id,
                    UserServiceAccess.service_id == service_id
                )
            )
            access = access_result.scalar_one_or_none()
            if not access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not have access to service {service_id}. Contact admin to grant access."
                )
    
    # Generate API key
    full_key, key_hash, key_prefix = generate_api_key()
    encrypted_key = encrypt_api_key(full_key)
    
    # Determine allowed_services - use the service_ids we determined above
    allowed_services = service_ids
    
    # Create API key
    api_key = ApiKey(
        user_id=current_user.id,
        name=key_data.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        encrypted_key=encrypted_key,
        allowed_services=allowed_services,
        whitelist_urls=key_data.whitelist_urls if key_data.whitelist_urls else None,
        status=ApiKeyStatus.ACTIVE
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    # Load services for response
    services_list = []
    if allowed_services:
        for svc_id in allowed_services:
            svc_result = await db.execute(
                select(Service)
                .where(Service.id == svc_id)
                .options(selectinload(Service.category))
            )
            svc = svc_result.scalar_one_or_none()
            if svc:
                services_list.append(ServiceResponse(
                    id=svc.id,
                    name=svc.name,
                    slug=svc.slug,
                    category_id=svc.category_id,
                    description=svc.description,
                    endpoint_path=svc.endpoint_path,
                    request_schema=svc.request_schema,
                    response_schema=svc.response_schema,
                    price_per_call=float(svc.price_per_call),
                    is_active=svc.is_active,
                    created_at=svc.created_at,
                    updated_at=svc.updated_at if svc.updated_at else svc.created_at,
                    category=None,
                    industries=None
                ))
    
    return APIKeyResponse(
        id=api_key.id,
        service_id=api_key.service_id,
        subscription_id=None,  # No subscriptions anymore
        key_prefix=api_key.key_prefix,
        full_key=full_key,  # Return full key on creation
        name=api_key.name,
        status=api_key.status.value,
        allowed_services=api_key.allowed_services,
        services=services_list if services_list else None,
        whitelist_urls=api_key.whitelist_urls,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys_by_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's API keys (supports multi-service keys)"""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == current_user.id)
        .options(selectinload(ApiKey.service))
        .order_by(ApiKey.created_at.desc())
    )
    api_keys = result.scalars().all()
    
    response_list = []
    for key in api_keys:
        # Load services for multi-service keys
        services_list = []
        if key.allowed_services:
            if "*" in key.allowed_services:
                # All services
                services_list = None  # Indicated by null in response
            else:
                # Load specific services
                for svc_id in key.allowed_services:
                    svc_result = await db.execute(select(Service).where(Service.id == svc_id))
                    svc = svc_result.scalar_one_or_none()
                    if svc:
                        services_list.append(ServiceResponse(
                            id=svc.id,
                            name=svc.name,
                            slug=svc.slug,
                            category_id=svc.category_id,
                            description=svc.description,
                            endpoint_path=svc.endpoint_path,
                            request_schema=svc.request_schema,
                            response_schema=svc.response_schema,
                            price_per_call=float(svc.price_per_call),
                            is_active=svc.is_active,
                            created_at=svc.created_at,
                            updated_at=svc.updated_at if svc.updated_at else svc.created_at,
                            category=None,
                            industries=None
                        ))
        
        # Backward compatibility: include service if single service key
        single_service = None
        if key.service:
            single_service = ServiceResponse(
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
            )
        
        # Decrypt full key if available
        full_key = None
        if key.encrypted_key:
            from app.core.security import decrypt_api_key
            full_key = decrypt_api_key(key.encrypted_key)
        
        response_list.append(APIKeyResponse(
            id=key.id,
            service_id=key.service_id,
            subscription_id=None,  # No subscriptions anymore
            key_prefix=key.key_prefix,
            full_key=full_key,  # Return decrypted full key
            name=key.name,
            status=key.status.value,
            allowed_services=key.allowed_services,
            whitelist_urls=key.whitelist_urls,
            last_used_at=key.last_used_at,
            created_at=key.created_at,
            service=single_service,
            services=services_list if services_list else None
        ))
    
    return response_list


@router.delete("/api-keys/{key_id}")
async def delete_api_key_duplicate(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key permanently from database"""
    result = await db.execute(
        select(ApiKey).where(
            and_(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    
    # Actually delete from database
    await db.execute(delete(ApiKey).where(ApiKey.id == key_id))
    await db.commit()

    return {"message": "API key deleted successfully"}


# Credit purchase removed - admin-only feature now
# Clients must contact admin to purchase credits with flexible pricing


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

