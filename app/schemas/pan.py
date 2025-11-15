from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class PANAddress(BaseModel):
    line_1: Optional[str] = None
    line_2: Optional[str] = None
    street_name: Optional[str] = None
    zip: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    full: Optional[str] = None


class PANIsDirector(BaseModel):
    found: str
    info: List[Dict[str, Any]] = []


class PANIsSoleProprietor(BaseModel):
    found: str
    info: List[Dict[str, Any]] = []


class PANDINInfo(BaseModel):
    din: Optional[str] = None
    dinAllocationDate: Optional[str] = None
    company_list: List[Any] = []


class PANResult(BaseModel):
    pan_number: str
    full_name: Optional[str] = None
    full_name_split: Optional[List[str]] = None
    masked_aadhaar: Optional[str] = None
    address: Optional[PANAddress] = None
    email: Optional[str] = None
    tax: Optional[bool] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    aadhaar_linked: Optional[bool] = None
    category: Optional[str] = None
    less_info: Optional[bool] = None
    is_director: Optional[PANIsDirector] = None
    is_sole_proprietor: Optional[PANIsSoleProprietor] = None
    fname: Optional[str] = None
    din_info: Optional[PANDINInfo] = None


class PANResponse(BaseModel):
    api_category: Optional[str] = None
    api_name: Optional[str] = None
    billable: Optional[bool] = None
    txn_id: Optional[str] = None
    message: str
    status: int
    result: Optional[PANResult] = None
    datetime: Optional[str] = None

