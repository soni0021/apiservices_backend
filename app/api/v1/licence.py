from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.licence import LicenceRequest, LicenceResponse
from app.middleware.api_key import verify_api_key
from app.middleware.usage_logger import UsageLoggerContext
from app.core.fallback_engine import FallbackEngine
from app.models.user import User
from app.models.api_key import ApiKey

router = APIRouter()


@router.post("/licence", response_model=LicenceResponse)
async def verify_licence(
    request_data: LicenceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, ApiKey] = Depends(verify_api_key)
):
    """Verify driving licence details"""
    user, api_key = auth
    
    # Create usage logger context
    async with UsageLoggerContext(
        db=db,
        user=user,
        api_key=api_key,
        endpoint_type="dl",
        request_params={"dl_no": request_data.dl_no, "dob": request_data.dob}
    ) as logger_ctx:
        
        # Create fallback engine
        engine = FallbackEngine(db)
        
        # Fetch data with fallback
        data, source = await engine.fetch_licence_data(request_data.dl_no, request_data.dob)
        
        if data is None:
            logger_ctx.set_status(404)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Licence data not found"
            )
        
        # Set data source for logging
        logger_ctx.set_source(source)
        logger_ctx.set_status(200)
        
        return data

