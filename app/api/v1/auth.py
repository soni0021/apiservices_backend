from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.schemas.auth import UserCreate, UserLogin, TokenResponse, UserResponse, RefreshTokenRequest
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new client user"""
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
    
    # Create new user with all mandatory fields
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
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
        total_credits=0,
        credits_used=0
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login and get access/refresh tokens"""
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    # Return user data along with tokens
    from app.schemas.auth import UserResponse
    user_response = UserResponse(
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
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    payload = decode_token(refresh_token_data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Create new tokens
    new_access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )

