from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
from app.database import get_db
from app.models.api_key import ApiKey, ApiKeyStatus
from app.models.user import User, UserStatus
from app.core.security import hash_api_key
from datetime import datetime


async def verify_api_key(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, ApiKey]:
    """
    Verify API key and return associated user and key
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )
    
    # Hash the provided key
    key_hash = hash_api_key(x_api_key)
    
    # Find the API key
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.status == ApiKeyStatus.ACTIVE
        )
    )
    api_key = result.scalar_one_or_none()
    
    if api_key is None:
        raise credentials_exception
    
    # Get associated user
    result = await db.execute(
        select(User).where(User.id == api_key.user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or not found"
        )
    
    # Update last_used_at (non-blocking)
    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key.id)
        .values(last_used_at=datetime.utcnow())
    )
    await db.commit()
    
    return user, api_key

