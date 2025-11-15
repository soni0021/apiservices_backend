from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    # New mandatory customer fields
    customer_name: str
    phone_number: str
    website_link: Optional[str] = None
    address: str
    gst_number: Optional[str] = None
    msme_certificate: Optional[str] = None
    aadhar_number: Optional[str] = None
    pan_number: Optional[str] = None
    birthday: Optional[date] = None
    about_me: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
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
    total_credits: float
    credits_used: float
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str

