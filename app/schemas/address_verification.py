from pydantic import BaseModel
from typing import Optional


class AddressVerificationData(BaseModel):
    dob: Optional[str] = None
    category: Optional[str] = None
    fullName: Optional[str] = None
    firstName: Optional[str] = None
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    aadhaarNo: Optional[str] = None
    responseType: Optional[int] = None


class AddressVerificationResponse(BaseModel):
    status: int
    message: str
    success: bool
    dataType: Optional[int] = None
    data: Optional[AddressVerificationData] = None

