from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.user import User, UserStatus
from app.models.api_key import ApiKey
from app.models.usage_log import ApiUsageLog
from app.models.system_config import SystemConfig
from app.models.industry import Industry
from app.models.category import Category
from app.models.service import Service
from app.models.service_industry import ServiceIndustry
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.transaction import Transaction, PaymentStatus
from app.middleware.auth import get_current_admin_user
from app.schemas.marketplace import (
    IndustryCreate, IndustryResponse,
    CategoryCreate, CategoryResponse,
    ServiceCreate, ServiceResponse,
    SubscriptionCreate, SubscriptionResponse
)
from app.websocket.manager import manager
from app.websocket.events import create_user_registration_event, create_subscription_event
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from decimal import Decimal

router = APIRouter()


# Schemas
class UserListResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    status: str
    created_at: datetime
    total_api_calls: int


class UserDetailResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str]
    role: str
    status: str
    created_at: datetime
    updated_at: datetime
    api_keys_count: int
    total_api_calls: int


class SystemAnalytics(BaseModel):
    total_users: int
    active_users: int
    total_api_calls: int
    calls_today: int
    calls_this_month: int
    by_endpoint: dict
    avg_response_time_ms: float


class ConfigUpdate(BaseModel):
    value: str


# Endpoints
@router.get("/users", response_model=List[UserListResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users (paginated)"""
    # Get users with API call counts
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    
    # Get API call counts for each user
    response = []
    for user in users:
        call_count_result = await db.execute(
            select(func.count(ApiUsageLog.id)).where(ApiUsageLog.user_id == user.id)
        )
        call_count = call_count_result.scalar() or 0
        
        response.append(UserListResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            status=user.status.value,
            created_at=user.created_at,
            total_api_calls=call_count
        ))
    
    return response


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed user information"""
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get API keys count
    keys_result = await db.execute(
        select(func.count(ApiKey.id)).where(ApiKey.user_id == user_id)
    )
    keys_count = keys_result.scalar() or 0
    
    # Get API calls count
    calls_result = await db.execute(
        select(func.count(ApiUsageLog.id)).where(ApiUsageLog.user_id == user_id)
    )
    calls_count = calls_result.scalar() or 0
    
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.value,
        status=user.status.value,
        created_at=user.created_at,
        updated_at=user.updated_at,
        api_keys_count=keys_count,
        total_api_calls=calls_count
    )


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    status_update: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user status"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if status_update in ["active", "inactive"]:
        user.status = UserStatus.ACTIVE if status_update == "active" else UserStatus.INACTIVE
        await db.commit()
        return {"message": "User status updated successfully"}
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid status"
    )


@router.get("/analytics", response_model=SystemAnalytics)
async def get_system_analytics(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system-wide analytics"""
    # Total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0
    
    # Active users
    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
    )
    active_users = active_users_result.scalar() or 0
    
    # Total API calls
    total_calls_result = await db.execute(select(func.count(ApiUsageLog.id)))
    total_api_calls = total_calls_result.scalar() or 0
    
    # Calls today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count(ApiUsageLog.id)).where(ApiUsageLog.created_at >= today_start)
    )
    calls_today = today_result.scalar() or 0
    
    # Calls this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_result = await db.execute(
        select(func.count(ApiUsageLog.id)).where(ApiUsageLog.created_at >= month_start)
    )
    calls_this_month = month_result.scalar() or 0
    
    # By endpoint
    endpoint_result = await db.execute(
        select(ApiUsageLog.endpoint_type, func.count(ApiUsageLog.id))
        .group_by(ApiUsageLog.endpoint_type)
    )
    by_endpoint = {row[0]: row[1] for row in endpoint_result.all()}
    
    # Average response time
    avg_time_result = await db.execute(
        select(func.avg(ApiUsageLog.response_time_ms))
    )
    avg_response_time_ms = avg_time_result.scalar() or 0
    
    return SystemAnalytics(
        total_users=total_users,
        active_users=active_users,
        total_api_calls=total_api_calls,
        calls_today=calls_today,
        calls_this_month=calls_this_month,
        by_endpoint=by_endpoint,
        avg_response_time_ms=float(avg_response_time_ms)
    )


@router.get("/usage-logs")
async def get_usage_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all API usage logs (paginated)"""
    result = await db.execute(
        select(ApiUsageLog)
        .order_by(ApiUsageLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()
    
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "endpoint_type": log.endpoint_type,
            "response_status": log.response_status,
            "response_time_ms": log.response_time_ms,
            "data_source": log.data_source,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]


@router.get("/configs")
async def get_configs(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all system configurations"""
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    
    return [
        {
            "key": config.key,
            "value": config.value,
            "description": config.description,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }
        for config in configs
    ]


@router.put("/configs/{key}")
async def update_config(
    key: str,
    config_update: ConfigUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a system configuration"""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    
    if not config:
        # Create new config
        config = SystemConfig(key=key, value=config_update.value)
        db.add(config)
    else:
        config.value = config_update.value
    
    await db.commit()
    return {"message": "Configuration updated successfully"}


# Marketplace Management Endpoints
@router.post("/industries", response_model=IndustryResponse, status_code=status.HTTP_201_CREATED)
async def create_industry(
    industry_data: IndustryCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new industry"""
    # Check if slug already exists
    result = await db.execute(
        select(Industry).where(Industry.slug == industry_data.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Industry with this slug already exists"
        )
    
    industry = Industry(**industry_data.dict())
    db.add(industry)
    await db.commit()
    await db.refresh(industry)
    return industry


@router.get("/industries", response_model=List[IndustryResponse])
async def list_industries(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all industries"""
    result = await db.execute(select(Industry).order_by(Industry.name))
    return result.scalars().all()


@router.put("/industries/{industry_id}", response_model=IndustryResponse)
async def update_industry(
    industry_id: str,
    industry_data: IndustryCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an industry"""
    result = await db.execute(select(Industry).where(Industry.id == industry_id))
    industry = result.scalar_one_or_none()
    
    if not industry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Industry not found")
    
    for key, value in industry_data.dict().items():
        setattr(industry, key, value)
    
    await db.commit()
    await db.refresh(industry)
    return industry


@router.delete("/industries/{industry_id}")
async def delete_industry(
    industry_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an industry"""
    result = await db.execute(select(Industry).where(Industry.id == industry_id))
    industry = result.scalar_one_or_none()
    
    if not industry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Industry not found")
    
    db.delete(industry)
    await db.commit()
    return {"message": "Industry deleted successfully"}


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new category"""
    result = await db.execute(
        select(Category).where(Category.slug == category_data.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this slug already exists"
        )
    
    category = Category(**category_data.dict())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all categories"""
    result = await db.execute(select(Category).order_by(Category.name))
    return result.scalars().all()


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    category_data: CategoryCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a category"""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    for key, value in category_data.dict().items():
        setattr(category, key, value)
    
    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a category"""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    db.delete(category)
    await db.commit()
    return {"message": "Category deleted successfully"}


@router.post("/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    service_data: ServiceCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new service with industry mappings"""
    result = await db.execute(
        select(Service).where(Service.slug == service_data.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service with this slug already exists"
        )
    
    # Create service
    service_dict = service_data.dict(exclude={"industry_ids"})
    service = Service(**service_dict)
    db.add(service)
    await db.flush()
    
    # Link to industries
    if service_data.industry_ids:
        for industry_id in service_data.industry_ids:
            service_industry = ServiceIndustry(
                service_id=service.id,
                industry_id=industry_id
            )
            db.add(service_industry)
    
    await db.commit()
    await db.refresh(service)
    
    # Load relationships
    result = await db.execute(
        select(Service)
        .where(Service.id == service.id)
        .options(selectinload(Service.category), selectinload(Service.service_industries))
    )
    service = result.scalar_one()
    
    return service


@router.get("/services", response_model=List[ServiceResponse])
async def list_services(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all services"""
    result = await db.execute(
        select(Service)
        .options(selectinload(Service.category), selectinload(Service.service_industries))
    )
    return result.scalars().all()


@router.put("/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: str,
    service_data: ServiceCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a service"""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    
    # Update service fields
    service_dict = service_data.dict(exclude={"industry_ids"})
    for key, value in service_dict.items():
        setattr(service, key, value)
    
    # Update industry mappings
    if service_data.industry_ids is not None:
        # Delete existing mappings
        await db.execute(
            select(ServiceIndustry).where(ServiceIndustry.service_id == service_id)
        )
        # Add new mappings
        for industry_id in service_data.industry_ids:
            service_industry = ServiceIndustry(
                service_id=service.id,
                industry_id=industry_id
            )
            db.add(service_industry)
    
    await db.commit()
    await db.refresh(service)
    return service


@router.delete("/services/{service_id}")
async def delete_service(
    service_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a service"""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    
    db.delete(service)
    await db.commit()
    return {"message": "Service deleted successfully"}


@router.get("/subscriptions")
async def list_subscriptions(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """View all user subscriptions"""
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.user), selectinload(Subscription.service))
        .order_by(Subscription.created_at.desc())
    )
    subscriptions = result.scalars().all()
    
    return [
        {
            "id": sub.id,
            "user_id": sub.user_id,
            "user_email": sub.user.email if sub.user else None,
            "service_id": sub.service_id,
            "service_name": sub.service.name if sub.service else None,
            "status": sub.status.value,
            "credits_allocated": float(sub.credits_allocated),
            "credits_remaining": float(sub.credits_remaining),
            "started_at": sub.started_at.isoformat(),
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            "created_at": sub.created_at.isoformat()
        }
        for sub in subscriptions
    ]


class AdminSubscriptionCreate(BaseModel):
    user_id: str
    service_id: str
    credits_allocated: Decimal
    expires_at: Optional[datetime] = None


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription_for_user(
    subscription_data: AdminSubscriptionCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin creates a subscription for a user"""
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == subscription_data.user_id))
    target_user = user_result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Check if service exists
    service_result = await db.execute(select(Service).where(Service.id == subscription_data.service_id))
    service = service_result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    
    # Refresh user from DB to get latest credits
    await db.refresh(target_user)
    
    # Check if user has sufficient credits
    user_credits = float(target_user.total_credits - target_user.credits_used)
    if user_credits < float(subscription_data.credits_allocated):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User has insufficient credits. Required: {subscription_data.credits_allocated}, Available: {user_credits}"
        )
    
    # Check if user already has an active subscription for this service
    existing_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == subscription_data.user_id,
            Subscription.service_id == subscription_data.service_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        )
    )
    existing_sub = existing_result.scalar_one_or_none()
    
    if existing_sub:
        # Deduct credits from user's account
        target_user.credits_used += Decimal(str(subscription_data.credits_allocated))
        # Update existing subscription
        existing_sub.credits_allocated += subscription_data.credits_allocated
        existing_sub.credits_remaining += subscription_data.credits_allocated
        if subscription_data.expires_at:
            existing_sub.expires_at = subscription_data.expires_at
        await db.commit()
        await db.refresh(existing_sub)
        await db.refresh(target_user)
        
        # Broadcast event
        await manager.send_personal_message(
            create_subscription_event(
                user_id=target_user.id,
                service_id=service.id,
                service_name=service.name,
                subscription_id=existing_sub.id,
                status=existing_sub.status.value,
                credits_allocated=float(existing_sub.credits_allocated)
            ),
            target_user.id
        )
        
        # Load service for response
        result = await db.execute(
            select(Subscription)
            .where(Subscription.id == existing_sub.id)
            .options(selectinload(Subscription.service))
        )
        updated_sub = result.scalar_one()
        
        return SubscriptionResponse(
            id=updated_sub.id,
            user_id=updated_sub.user_id,
            service_id=updated_sub.service_id,
            status=updated_sub.status.value,
            credits_allocated=float(updated_sub.credits_allocated),
            credits_remaining=float(updated_sub.credits_remaining),
            started_at=updated_sub.started_at,
            expires_at=updated_sub.expires_at,
            created_at=updated_sub.created_at,
            updated_at=updated_sub.updated_at,
            service=ServiceResponse(
                id=updated_sub.service.id,
                name=updated_sub.service.name,
                slug=updated_sub.service.slug,
                category_id=updated_sub.service.category_id,
                description=updated_sub.service.description,
                endpoint_path=updated_sub.service.endpoint_path,
                request_schema=updated_sub.service.request_schema,
                response_schema=updated_sub.service.response_schema,
                price_per_call=float(updated_sub.service.price_per_call),
                is_active=updated_sub.service.is_active,
                created_at=updated_sub.service.created_at,
                updated_at=updated_sub.service.updated_at,
                category=None,
                industries=None
            ) if updated_sub.service else None
        )
    
    # Deduct credits from user's account
    target_user.credits_used += Decimal(str(subscription_data.credits_allocated))
    
    # Create new subscription
    subscription = Subscription(
        user_id=subscription_data.user_id,
        service_id=subscription_data.service_id,
        status=SubscriptionStatus.ACTIVE,
        credits_allocated=subscription_data.credits_allocated,
        credits_remaining=subscription_data.credits_allocated,
        started_at=datetime.utcnow(),
        expires_at=subscription_data.expires_at
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    await db.refresh(target_user)
    
    # Load service for response
    result = await db.execute(
        select(Subscription)
        .where(Subscription.id == subscription.id)
        .options(selectinload(Subscription.service))
    )
    new_sub = result.scalar_one()
    
    # Broadcast event
    await manager.send_personal_message(
        create_subscription_event(
            user_id=target_user.id,
            service_id=service.id,
            service_name=service.name,
            subscription_id=new_sub.id,
            status=new_sub.status.value,
            credits_allocated=float(new_sub.credits_allocated)
        ),
        target_user.id
    )
    
    return SubscriptionResponse(
        id=new_sub.id,
        user_id=new_sub.user_id,
        service_id=new_sub.service_id,
        status=new_sub.status.value,
        credits_allocated=float(new_sub.credits_allocated),
        credits_remaining=float(new_sub.credits_remaining),
        started_at=new_sub.started_at,
        expires_at=new_sub.expires_at,
        created_at=new_sub.created_at,
        updated_at=new_sub.updated_at,
        service=ServiceResponse(
            id=new_sub.service.id,
            name=new_sub.service.name,
            slug=new_sub.service.slug,
            category_id=new_sub.service.category_id,
            description=new_sub.service.description,
            endpoint_path=new_sub.service.endpoint_path,
            request_schema=new_sub.service.request_schema,
            response_schema=new_sub.service.response_schema,
            price_per_call=float(new_sub.service.price_per_call),
            is_active=new_sub.service.is_active,
            created_at=new_sub.service.created_at,
            updated_at=new_sub.service.updated_at,
            category=None,
            industries=None
        ) if new_sub.service else None
    )


@router.get("/transactions")
async def list_transactions(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """View all credit purchases"""
    result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.user))
        .order_by(Transaction.created_at.desc())
    )
    transactions = result.scalars().all()
    
    return [
        {
            "id": txn.id,
            "user_id": txn.user_id,
            "user_email": txn.user.email if txn.user else None,
            "amount_paid": float(txn.amount_paid),
            "credits_purchased": float(txn.credits_purchased),
            "payment_method": txn.payment_method,
            "payment_status": txn.payment_status.value,
            "transaction_id": txn.transaction_id,
            "created_at": txn.created_at.isoformat()
        }
        for txn in transactions
    ]


@router.get("/realtime-stats")
async def get_realtime_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get real-time platform statistics"""
    # Total users
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    
    # Active users
    active_users = (await db.execute(
        select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
    )).scalar() or 0
    
    # Total API calls
    total_calls = (await db.execute(select(func.count(ApiUsageLog.id)))).scalar() or 0
    
    # Total revenue (sum of all transactions)
    total_revenue = (await db.execute(
        select(func.sum(Transaction.amount_paid))
        .where(Transaction.payment_status == PaymentStatus.COMPLETED)
    )).scalar() or 0
    
    # Total credits purchased
    total_credits = (await db.execute(
        select(func.sum(Transaction.credits_purchased))
        .where(Transaction.payment_status == PaymentStatus.COMPLETED)
    )).scalar() or 0
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_api_calls": total_calls,
        "total_revenue": float(total_revenue),
        "total_credits_purchased": float(total_credits)
    }

