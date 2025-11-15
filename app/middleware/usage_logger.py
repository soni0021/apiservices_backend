from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usage_log import ApiUsageLog
from app.models.user import User
from app.models.api_key import ApiKey
from typing import Optional
import time


async def log_api_usage(
    db: AsyncSession,
    user: User,
    api_key: Optional[ApiKey],
    endpoint_type: str,
    request_params: dict,
    response_status: int,
    response_time_ms: int,
    data_source: str
):
    """Log an API usage"""
    usage_log = ApiUsageLog(
        user_id=user.id,
        api_key_id=api_key.id if api_key else None,
        endpoint_type=endpoint_type,
        request_params=request_params,
        response_status=response_status,
        response_time_ms=response_time_ms,
        data_source=data_source
    )
    db.add(usage_log)
    await db.commit()


class UsageLoggerContext:
    """Context manager for logging API usage with timing"""
    
    def __init__(
        self,
        db: AsyncSession,
        user: User,
        api_key: Optional[ApiKey],
        endpoint_type: str,
        request_params: dict
    ):
        self.db = db
        self.user = user
        self.api_key = api_key
        self.endpoint_type = endpoint_type
        self.request_params = request_params
        self.start_time = None
        self.response_status = 200
        self.data_source = "unknown"
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        response_time_ms = int((time.time() - self.start_time) * 1000)
        
        if exc_type:
            self.response_status = 500
        
        await log_api_usage(
            self.db,
            self.user,
            self.api_key,
            self.endpoint_type,
            self.request_params,
            self.response_status,
            response_time_ms,
            self.data_source
        )
    
    def set_source(self, source: str):
        """Set the data source (db, api1, api2, api3)"""
        self.data_source = source
    
    def set_status(self, status: int):
        """Set the response status"""
        self.response_status = status

