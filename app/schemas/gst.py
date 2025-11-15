from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class GSTBusinessDetails(BaseModel):
    bzsdtls: Optional[List[Dict[str, str]]] = None


class GSTPrimaryAddress(BaseModel):
    business_nature: Optional[str] = None
    detailed_address: Optional[str] = None
    last_updated_date: Optional[str] = None
    registered_address: Optional[str] = None


class GSTFilingStatus(BaseModel):
    fy: Optional[str] = None
    taxp: Optional[str] = None
    mof: Optional[str] = None
    dof: Optional[str] = None
    rtntype: Optional[str] = None
    arn: Optional[str] = None
    status: Optional[str] = None


class GSTResult(BaseModel):
    aggregate_turn_over: Optional[str] = None
    authorized_signatory: Optional[List[str]] = None
    business_constitution: Optional[str] = None
    business_details: Optional[GSTBusinessDetails] = None
    business_nature: Optional[List[str]] = None
    can_flag: Optional[str] = None
    central_jurisdiction: Optional[str] = None
    compliance_rating: Optional[str] = None
    current_registration_status: Optional[str] = None
    filing_status: Optional[List[List[GSTFilingStatus]]] = None
    gstin: str
    is_field_visit_conducted: Optional[str] = None
    legal_name: Optional[str] = None
    mandate_e_invoice: Optional[str] = None
    other_business_address: Optional[Dict[str, Any]] = None
    primary_business_address: Optional[GSTPrimaryAddress] = None
    register_cancellation_date: Optional[str] = None
    register_date: Optional[str] = None
    state_jurisdiction: Optional[str] = None
    tax_payer_type: Optional[str] = None
    trade_name: Optional[str] = None
    gross_total_income: Optional[str] = None
    gross_total_income_financial_year: Optional[str] = None


class GSTResponse(BaseModel):
    api_category: Optional[str] = None
    api_name: Optional[str] = None
    billable: Optional[bool] = None
    txn_id: Optional[str] = None
    message: str
    status: int
    result: Optional[GSTResult] = None
    datetime: Optional[str] = None

