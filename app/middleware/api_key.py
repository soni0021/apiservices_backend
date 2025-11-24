from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
from app.database import get_db
from app.models.api_key import ApiKey, ApiKeyStatus
from app.models.user import User, UserStatus
from app.core.security import hash_api_key
from datetime import datetime
from urllib.parse import urlparse


def check_whitelist_url(api_key: ApiKey, request: Request) -> bool:
    """
    Check if request origin is in whitelist URLs
    Returns True if whitelist is empty/null (no restriction) or origin matches
    """
    if not api_key.whitelist_urls or len(api_key.whitelist_urls) == 0:
        return True  # No restriction
    
    # Get origin from request
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if not origin:
        return False  # No origin header, reject if whitelist exists
    
    # Parse origin to get domain
    try:
        origin_parsed = urlparse(origin)
        origin_domain = f"{origin_parsed.scheme}://{origin_parsed.netloc}"
    except:
        return False
    
    # Check if origin matches any whitelist URL
    for whitelist_url in api_key.whitelist_urls:
        try:
            whitelist_parsed = urlparse(whitelist_url)
            whitelist_domain = f"{whitelist_parsed.scheme}://{whitelist_parsed.netloc}"
            
            # Exact match or subdomain match
            if origin_domain == whitelist_domain or origin_domain.endswith(f".{whitelist_parsed.netloc}"):
                return True
        except:
            continue
    
    return False


async def verify_api_key(
    request: Request,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, ApiKey]:
    """
    Verify API key and return associated user and key
    Also checks whitelist URLs if configured
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
    
    # Check whitelist URLs if configured
    if not check_whitelist_url(api_key, request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request origin not whitelisted for this API key"
        )
    
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

