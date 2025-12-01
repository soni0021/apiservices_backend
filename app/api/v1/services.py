"""
Generic service execution endpoint
Handles all service types with API key validation, user service access check, and credit deduction
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Dict, Any
from app.database import get_db
from app.models.service import Service
from app.models.api_key import ApiKey, ApiKeyStatus
from app.models.user import User, UserStatus
from app.middleware.api_key import verify_api_key
from app.core.service_engine import ServiceEngine
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/services/{service_slug}")
async def execute_service(
    service_slug: str,
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, ApiKey] = Depends(verify_api_key)
):
    """
    Generic service execution endpoint
    
    Validates:
    1. API key exists and is active (with whitelist URL check)
    2. Service exists and is active
    3. API key has access to the requested service
    4. User has access to the service (via user_service_access)
    5. User has sufficient credits
    
    Executes service and deducts credits
    """
    user, api_key = auth
    
    # 2. Get service
    result = await db.execute(
        select(Service).where(
            Service.slug == service_slug,
            Service.is_active == True
        )
    )
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_slug}' not found or inactive"
        )
    
    # 3. Verify API key has access to this service
    has_access = False
    access_reason = ""
    
    if api_key.allowed_services:
        if "*" in api_key.allowed_services:
            has_access = True  # All services access
            access_reason = "all services (wildcard)"
        elif service.id in api_key.allowed_services:
            has_access = True  # Specific service in allowed list
            access_reason = f"service '{service.name}' in allowed list"
    elif api_key.service_id == service.id:
        has_access = True  # Backward compatibility: single service key
        access_reason = f"service_id match"
    
    if not has_access:
        # Provide detailed error message
        allowed_info = "all services" if (api_key.allowed_services and "*" in api_key.allowed_services) else f"{len(api_key.allowed_services or [])} specific service(s)"
        error_msg = (
            f"API key does not have access to service '{service_slug}' ({service.name}). "
            f"This key has access to: {allowed_info}. "
            f"Contact admin to grant access to this service."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg
        )
    
    # Log access granted for debugging
    logger.info(f"API key {api_key.id} granted access to {service_slug} ({access_reason})")
    
    # 4. Execute service (service engine will check user service access and credits)
    try:
        service_engine = ServiceEngine(db)
        result = await service_engine.execute_service(
            service=service,
            api_key=api_key,
            payload=payload
        )
        return result
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 for data not found)
        raise
    except ValueError as e:
        # ValueError for missing required parameters should be 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error executing service {service_slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service execution failed"
        )


@router.get("/services")
async def list_services(
    db: AsyncSession = Depends(get_db)
):
    """List all active services"""
    result = await db.execute(
        select(Service)
        .where(Service.is_active == True)
        .options(selectinload(Service.category))
    )
    services = result.scalars().all()
    
    return [
        {
            "id": service.id,
            "name": service.name,
            "slug": service.slug,
            "description": service.description,
            "category": {
                "id": service.category.id if service.category else None,
                "name": service.category.name if service.category else None,
                "slug": service.category.slug if service.category else None
            } if service.category else None,
            "endpoint_path": service.endpoint_path,
            "price_per_call": float(service.price_per_call),
            "is_active": service.is_active
        }
        for service in services
    ]


@router.get("/services/{service_slug}")
async def get_service_details(
    service_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get service details"""
    result = await db.execute(
        select(Service)
        .where(Service.slug == service_slug)
        .options(selectinload(Service.category))
    )
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    return {
        "id": service.id,
        "name": service.name,
        "slug": service.slug,
        "description": service.description,
        "category": {
            "id": service.category.id if service.category else None,
            "name": service.category.name if service.category else None,
            "slug": service.category.slug if service.category else None
        } if service.category else None,
        "endpoint_path": service.endpoint_path,
        "request_schema": service.request_schema,
        "response_schema": service.response_schema,
        "price_per_call": float(service.price_per_call),
        "is_active": service.is_active
    }

