from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete
from typing import List, Optional
from datetime import datetime, date, date
from app.database import get_db
from app.models.user import User, UserStatus
from app.models.api_key import ApiKey
from app.models.usage_log import ApiUsageLog
from app.models.system_config import SystemConfig
from app.models.industry import Industry
from app.models.category import Category
from app.models.service import Service
from app.models.service_industry import ServiceIndustry
from app.models.user_service_access import UserServiceAccess
from app.models.transaction import Transaction, PaymentStatus
from app.middleware.auth import get_current_admin_user
from app.schemas.marketplace import (
    IndustryCreate, IndustryResponse,
    CategoryCreate, CategoryResponse,
    ServiceCreate, ServiceResponse
)
from app.schemas.auth import UserCreate, UserResponse
from app.models.user import UserRole
from app.websocket.manager import manager
from app.websocket.events import create_user_registration_event
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from decimal import Decimal
import uuid

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
    customer_name: Optional[str]
    phone_number: Optional[str]
    website_link: Optional[str]
    address: Optional[str]
    gst_number: Optional[str]
    msme_certificate: Optional[str]
    aadhar_number: Optional[str]
    pan_number: Optional[str]
    birthday: Optional[date]
    about_me: Optional[str]
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
        full_name=user.full_name or "",
        phone=user.phone,
        customer_name=user.customer_name,
        phone_number=user.phone_number,
        website_link=user.website_link,
        address=user.address,
        gst_number=user.gst_number,
        msme_certificate=user.msme_certificate,
        aadhar_number=user.aadhar_number,
        pan_number=user.pan_number,
        birthday=user.birthday,
        about_me=user.about_me,
        role=user.role.value,
        status=user.status.value,
        created_at=user.created_at,
        updated_at=user.updated_at,
        api_keys_count=keys_count,
        total_api_calls=calls_count
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin creates a new client user (same signup flow)"""
    from app.core.security import get_password_hash
    
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user - only email and password required, other fields optional
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name or "",
        phone=user_data.phone,
        customer_name=user_data.customer_name,
        phone_number=user_data.phone_number,
        website_link=user_data.website_link,
        address=user_data.address,
        gst_number=user_data.gst_number,
        msme_certificate=user_data.msme_certificate,
        aadhar_number=user_data.aadhar_number,
        pan_number=user_data.pan_number,
        birthday=user_data.birthday,
        about_me=user_data.about_me,
        role=UserRole.CLIENT,
        status=UserStatus.INACTIVE,  # New users are inactive by default - admin must activate or payment activates
        total_credits=0,
        credits_used=0
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Return user response
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name or "",
        phone=new_user.phone,
        customer_name=new_user.customer_name,
        phone_number=new_user.phone_number,
        website_link=new_user.website_link,
        address=new_user.address,
        gst_number=new_user.gst_number,
        msme_certificate=new_user.msme_certificate,
        aadhar_number=new_user.aadhar_number,
        pan_number=new_user.pan_number,
        birthday=new_user.birthday,
        about_me=new_user.about_me,
        total_credits=float(new_user.total_credits),
        credits_used=float(new_user.credits_used),
        role=new_user.role.value if hasattr(new_user.role, 'value') else str(new_user.role),
        status=new_user.status.value if hasattr(new_user.status, 'value') else str(new_user.status),
        created_at=new_user.created_at,
        updated_at=new_user.updated_at
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user (admin only)"""
    # Prevent admin from deleting themselves
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting admin users
    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin users"
        )
    
    # Delete user (cascade will handle related records)
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    
    return {"message": "User deleted successfully"}


class UserStatusUpdate(BaseModel):
    status: str  # "active" or "inactive"


@router.put("/users/{user_id}/status", status_code=status.HTTP_200_OK)
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user status (activate/deactivate)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if status_update.status not in ["active", "inactive"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'active' or 'inactive'"
        )
    
    user.status = UserStatus.ACTIVE if status_update.status == "active" else UserStatus.INACTIVE
    await db.commit()
    await db.refresh(user)
    
    return {"message": f"User status updated to {status_update.status} successfully", "status": user.status.value}


class UserUpdate(BaseModel):
    """Update user information"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    website_link: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    msme_certificate: Optional[str] = None
    aadhar_number: Optional[str] = None
    pan_number: Optional[str] = None
    birthday: Optional[date] = None
    about_me: Optional[str] = None


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user information"""
    from pydantic import EmailStr, validate_email
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent updating admin users
    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update admin users"
        )
    
    # Check if email is being changed and if it already exists
    if user_update.email and user_update.email != user.email:
        # Validate email format
        try:
            validate_email(user_update.email)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        existing_result = await db.execute(
            select(User).where(User.email == user_update.email)
        )
        existing_user = existing_result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = user_update.email
    
    # Update other fields if provided
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.phone is not None:
        user.phone = user_update.phone
    if user_update.customer_name is not None:
        user.customer_name = user_update.customer_name
    if user_update.phone_number is not None:
        user.phone_number = user_update.phone_number
    if user_update.website_link is not None:
        user.website_link = user_update.website_link
    if user_update.address is not None:
        user.address = user_update.address
    if user_update.gst_number is not None:
        user.gst_number = user_update.gst_number
    if user_update.msme_certificate is not None:
        user.msme_certificate = user_update.msme_certificate
    if user_update.aadhar_number is not None:
        user.aadhar_number = user_update.aadhar_number
    if user_update.pan_number is not None:
        user.pan_number = user_update.pan_number
    if user_update.birthday is not None:
        user.birthday = user_update.birthday
    if user_update.about_me is not None:
        user.about_me = user_update.about_me
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name or "",
        phone=user.phone,
        customer_name=user.customer_name,
        phone_number=user.phone_number,
        website_link=user.website_link,
        address=user.address,
        gst_number=user.gst_number,
        msme_certificate=user.msme_certificate,
        aadhar_number=user.aadhar_number,
        pan_number=user.pan_number,
        birthday=user.birthday,
        about_me=user.about_me,
        total_credits=float(user.total_credits),
        credits_used=float(user.credits_used),
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        status=user.status.value if hasattr(user.status, 'value') else str(user.status),
        created_at=user.created_at,
        updated_at=user.updated_at
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


# Subscription endpoints removed - replaced with service access management
# See service access management endpoints below


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


# Admin API Key Management
from app.schemas.marketplace import AdminAPIKeyGenerateRequest, APIKeyResponse
from app.models.api_key import ApiKey, ApiKeyStatus
from app.core.security import generate_api_key

@router.post("/api-keys/generate", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def admin_generate_api_key(
    key_request: AdminAPIKeyGenerateRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin generates API key for a user with service access and whitelist URLs"""
    try:
        # Verify user exists
        user_result = await db.execute(select(User).where(User.id == key_request.user_id))
        target_user = user_result.scalar_one_or_none()
        
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # Validate service_ids
        if not key_request.service_ids or len(key_request.service_ids) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one service ID must be provided"
            )
        
        # Check for all services access
        if "*" in key_request.service_ids:
            service_ids = ["*"]
            primary_service_id = None
        else:
            # Validate each service exists
            service_ids = key_request.service_ids
            for service_id in service_ids:
                svc_result = await db.execute(select(Service).where(Service.id == service_id))
                service = svc_result.scalar_one_or_none()
                if not service:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Service {service_id} not found"
                    )
            primary_service_id = service_ids[0] if len(service_ids) == 1 else None
        
        # Generate API key
        full_key, key_hash, key_prefix = generate_api_key("sk_live")
        
        # Encrypt full key for storage
        from app.core.security import encrypt_api_key
        encrypted_key = encrypt_api_key(full_key)
        
        # Create API key record
        api_key = ApiKey(
            user_id=key_request.user_id,
            service_id=primary_service_id,
            subscription_id=None,  # Admin-generated keys don't require subscription
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=key_request.name,
            status=ApiKeyStatus.ACTIVE,
            allowed_services=service_ids,
            whitelist_urls=key_request.whitelist_urls or [],
            encrypted_key=encrypted_key
        )
        
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        
        # Load services for response
        services_response = []
        if "*" not in service_ids:
            for service_id in service_ids:
                svc_result = await db.execute(select(Service).where(Service.id == service_id))
                svc = svc_result.scalar_one_or_none()
                if svc:
                    updated_at = svc.updated_at if svc.updated_at else svc.created_at
                    services_response.append(ServiceResponse(
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
                        updated_at=updated_at,
                category=None,
                industries=None
                    ))
        
        return APIKeyResponse(
            id=api_key.id,
            service_id=api_key.service_id,
            subscription_id=None,  # No subscriptions anymore
            key_prefix=api_key.key_prefix,
            full_key=full_key,  # Only shown once
            name=api_key.name,
            status=api_key.status.value,
            allowed_services=service_ids,
            whitelist_urls=api_key.whitelist_urls,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            service=services_response[0] if len(services_response) == 1 else None,
            services=services_response if len(services_response) > 0 else None
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


@router.get("/users/{user_id}/api-keys", response_model=List[APIKeyResponse])
async def get_user_api_keys(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all API keys for a specific user"""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id)
        .options(selectinload(ApiKey.service))
        .order_by(ApiKey.created_at.desc())
    )
    api_keys = result.scalars().all()
    
    response_list = []
    for key in api_keys:
        services_list = []
        if key.allowed_services:
            if "*" not in key.allowed_services:
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
        
        response_list.append(APIKeyResponse(
            id=key.id,
            service_id=key.service_id,
            subscription_id=None,  # No subscriptions anymore
            key_prefix=key.key_prefix,
            full_key=None,  # Never return full key in list
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


# Credit Management Endpoints
class CreditAllocation(BaseModel):
    """Admin allocates credits to user"""
    credits_amount: Decimal
    amount_paid: Optional[Decimal] = None  # Optional: track payment if any
    notes: Optional[str] = None


@router.post("/users/{user_id}/credits")
async def allocate_credits_to_user(
    user_id: str,
    credit_data: CreditAllocation,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin allocates credits to a user (with flexible pricing)"""
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Add credits to user
    user.total_credits += credit_data.credits_amount
    
    # Create transaction record if payment info provided
    if credit_data.amount_paid and credit_data.amount_paid > 0:
        transaction = Transaction(
            user_id=user_id,
            amount_paid=credit_data.amount_paid,
            credits_purchased=credit_data.credits_amount,
            payment_method="admin_allocation",
            payment_status=PaymentStatus.COMPLETED,
            transaction_id=f"ADMIN-{uuid.uuid4().hex[:12].upper()}"
        )
        db.add(transaction)
        
        # Auto-activate user after payment
        if user.status == UserStatus.INACTIVE:
            user.status = UserStatus.ACTIVE
    
    await db.commit()
    await db.refresh(user)
    
    return {
        "message": "Credits allocated successfully",
        "user_id": user_id,
        "credits_allocated": float(credit_data.credits_amount),
        "total_credits": float(user.total_credits),
        "credits_remaining": float(user.total_credits - user.credits_used)
    }


class UserPricingUpdate(BaseModel):
    """Update user's per-credit pricing"""
    price_per_credit: Decimal  # Rupees per credit


@router.put("/users/{user_id}/pricing")
async def update_user_pricing(
    user_id: str,
    pricing_data: UserPricingUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin sets custom per-credit pricing for a specific user"""
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if pricing_data.price_per_credit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price per credit must be greater than 0"
        )
    
    user.price_per_credit = pricing_data.price_per_credit
    await db.commit()
    await db.refresh(user)
    
    return {
        "message": "User pricing updated successfully",
        "user_id": user_id,
        "price_per_credit": float(user.price_per_credit)
    }


@router.get("/users/{user_id}/credits")
async def get_user_credit_info(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed credit information for a user"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "total_credits": float(user.total_credits),
        "credits_used": float(user.credits_used),
        "credits_remaining": float(user.total_credits - user.credits_used),
        "price_per_credit": float(user.price_per_credit),
        "effective_balance_value": float((user.total_credits - user.credits_used) * user.price_per_credit)
    }


# Service Access Management Endpoints
class UserServiceAccessCreate(BaseModel):
    """Grant service access to a user"""
    service_id: str


class UserServiceAccessResponse(BaseModel):
    """Service access response"""
    id: str
    user_id: str
    service_id: str
    service: Optional[ServiceResponse] = None
    granted_by: Optional[str] = None
    granted_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/users/{user_id}/service-access", response_model=UserServiceAccessResponse, status_code=status.HTTP_201_CREATED)
async def grant_service_access(
    user_id: str,
    access_data: UserServiceAccessCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Grant a user access to a service"""
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Verify service exists
    service_result = await db.execute(select(Service).where(Service.id == access_data.service_id))
    service = service_result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    
    # Check if access already exists
    existing_result = await db.execute(
        select(UserServiceAccess).where(
            and_(
                UserServiceAccess.user_id == user_id,
                UserServiceAccess.service_id == access_data.service_id
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has access to this service"
        )
    
    # Create service access
    service_access = UserServiceAccess(
        user_id=user_id,
        service_id=access_data.service_id,
        granted_by=current_admin.id
    )
    
    db.add(service_access)
    await db.commit()
    await db.refresh(service_access)
    
    # Load service for response
    service_response = ServiceResponse(
        id=service.id,
        name=service.name,
        slug=service.slug,
        category_id=service.category_id,
        description=service.description,
        endpoint_path=service.endpoint_path,
        request_schema=service.request_schema,
        response_schema=service.response_schema,
        price_per_call=float(service.price_per_call),
        is_active=service.is_active,
        created_at=service.created_at,
        updated_at=service.updated_at if service.updated_at else service.created_at,
        category=None,
        industries=None
    )
    
    return UserServiceAccessResponse(
        id=service_access.id,
        user_id=service_access.user_id,
        service_id=service_access.service_id,
        service=service_response,
        granted_by=service_access.granted_by,
        granted_at=service_access.granted_at,
        created_at=service_access.created_at
    )


@router.delete("/users/{user_id}/service-access/{service_id}", status_code=status.HTTP_200_OK)
async def revoke_service_access(
    user_id: str,
    service_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a user's access to a service"""
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Find and delete service access
    access_result = await db.execute(
        select(UserServiceAccess).where(
            and_(
                UserServiceAccess.user_id == user_id,
                UserServiceAccess.service_id == service_id
            )
        )
    )
    access = access_result.scalar_one_or_none()
    
    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service access not found"
        )
    
    from sqlalchemy import delete
    await db.execute(delete(UserServiceAccess).where(UserServiceAccess.id == access.id))
    await db.commit()
    
    return {"message": "Service access revoked successfully"}


@router.get("/users/{user_id}/service-access", response_model=List[UserServiceAccessResponse])
async def list_user_service_access(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all services a user has access to"""
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Get all service access records
    access_result = await db.execute(
        select(UserServiceAccess)
        .where(UserServiceAccess.user_id == user_id)
    )
    access_records = access_result.scalars().all()
    
    response_list = []
    for access in access_records:
        # Load service details
        service_result = await db.execute(select(Service).where(Service.id == access.service_id))
        service = service_result.scalar_one_or_none()
        
        service_response = None
        if service:
            service_response = ServiceResponse(
                id=service.id,
                name=service.name,
                slug=service.slug,
                category_id=service.category_id,
                description=service.description,
                endpoint_path=service.endpoint_path,
                request_schema=service.request_schema,
                response_schema=service.response_schema,
                price_per_call=float(service.price_per_call),
                is_active=service.is_active,
                created_at=service.created_at,
                updated_at=service.updated_at if service.updated_at else service.created_at,
                category=None,
                industries=None
            )
        
        response_list.append(UserServiceAccessResponse(
            id=access.id,
            user_id=access.user_id,
            service_id=access.service_id,
            service=service_response,
            granted_by=access.granted_by,
            granted_at=access.granted_at,
            created_at=access.created_at
        ))
    
    return response_list

