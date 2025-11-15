from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.challan import ChallanRequest, ChallanResponse
from app.middleware.api_key import verify_api_key
from app.middleware.usage_logger import UsageLoggerContext
from app.core.fallback_engine import FallbackEngine
from app.models.user import User
from app.models.api_key import ApiKey

router = APIRouter()


@router.post("/challan", response_model=ChallanResponse)
async def verify_challan(
    request: ChallanRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, ApiKey] = Depends(verify_api_key)
):
    """Get vehicle challan/violation details"""
    user, api_key = auth
    
    # Create usage logger context
    async with UsageLoggerContext(
        db=db,
        user=user,
        api_key=api_key,
        endpoint_type="challan",
        request_params={"vehicle_no": request.vehicle_no}
    ) as logger_ctx:
        
        # Create fallback engine
        engine = FallbackEngine(db)
        
        # Fetch data with fallback
        data, source = await engine.fetch_challan_data(request.vehicle_no)
        
        if data is None:
            logger_ctx.set_status(404)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challan data not found"
            )
        
        # Set data source for logging
        logger_ctx.set_source(source)
        logger_ctx.set_status(200)
        
        return data

