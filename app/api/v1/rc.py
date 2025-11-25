from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.rc import RCRequest, RCResponse
from app.middleware.api_key import verify_api_key
from app.middleware.usage_logger import UsageLoggerContext
from app.core.fallback_engine import FallbackEngine
from app.models.user import User
from app.models.api_key import ApiKey

router = APIRouter()


@router.post("/rc", response_model=RCResponse)
async def verify_rc(
    request_data: RCRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, ApiKey] = Depends(verify_api_key)
):
    """Verify vehicle RC details"""
    user, api_key = auth
    
    # Create usage logger context
    async with UsageLoggerContext(
        db=db,
        user=user,
        api_key=api_key,
        endpoint_type="rc",
        request_params={"reg_no": request_data.reg_no}
    ) as logger_ctx:
        
        # Create fallback engine
        engine = FallbackEngine(db)
        
        # Fetch data with fallback
        data, source = await engine.fetch_rc_data(request_data.reg_no)
        
        if data is None:
            logger_ctx.set_status(404)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RC data not found"
            )
        
        # Set data source for logging
        logger_ctx.set_source(source)
        logger_ctx.set_status(200)
        
        return data

