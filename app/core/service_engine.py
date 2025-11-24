"""
Unified service execution engine
Handles all service types with subscription validation, credit deduction, and WebSocket broadcasting
"""
import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.service import Service
from app.models.api_key import ApiKey
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.models.usage_log import ApiUsageLog
from app.core.fallback_engine import FallbackEngine
from app.models.rc_data import RCData
from app.models.rc_mobile_data import RCMobileData
from app.models.licence_data import LicenceData, LicenceCoverage
from app.models.challan_data import ChallanData, ChallanRecord, ChallanOffence
from app.models.pan_data import PANData
from app.models.address_verification_data import AddressVerificationData
from app.models.fuel_price_data import FuelPriceData
from app.models.gst_data import GSTData
from app.models.msme_data import MSMEData
from app.models.udyam_data import UdyamData
from app.models.voter_id_data import VoterIDData
from app.models.dl_challan_data import DLChallanData
from app.config import get_settings
from app.websocket.manager import manager
from app.websocket.events import (
    create_api_call_event,
    create_credit_balance_update_event
)
import logging

settings = get_settings()
logger = logging.getLogger(__name__)


class ServiceEngine:
    """Unified service execution engine"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.fallback_engine = FallbackEngine(db)
    
    async def execute_service(
        self,
        service: Service,
        api_key: ApiKey,
        subscription: Optional[Subscription],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a service with full validation and credit deduction
        
        Steps:
        1. Validate subscription (if exists) or check user credits
        2. Check credit balance >= service.price_per_call
        3. Execute service logic based on service.slug
        4. Deduct credits from subscription (if exists) or user directly
        5. Log usage with credits
        6. Broadcast to WebSocket
        7. Return result
        """
        start_time = time.time()
        
        # Get user for credit tracking
        user_result = await self.db.execute(select(User).where(User.id == api_key.user_id))
        user = user_result.scalar_one()
        
        credits_needed = service.price_per_call
        user_credits_before = float(user.total_credits - user.credits_used)
        
        # 1. Validate subscription or check user credits
        if subscription:
            # Subscription-based flow
            if subscription.status != SubscriptionStatus.ACTIVE:
                raise ValueError("Subscription is not active")
            
            # Check if subscription has expired (handle timezone-aware/naive comparison)
            if subscription.expires_at:
                now = datetime.now(timezone.utc)
                expires_at = subscription.expires_at
                # Make expires_at timezone-aware if it's naive
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < now:
                    raise ValueError("Subscription has expired")
            
            # 2. Check credit balance from subscription
            if subscription.credits_remaining < credits_needed:
                raise ValueError(f"Insufficient credits. Required: {credits_needed}, Available: {subscription.credits_remaining}")
            
            credits_before = float(subscription.credits_remaining)
        else:
            # Admin-generated key without subscription - use user credits directly
            if user_credits_before < float(credits_needed):
                raise ValueError(f"Insufficient credits. Required: {credits_needed}, Available: {user_credits_before}")
            
            credits_before = user_credits_before
        
        # 3. Execute service logic
        try:
            result = await self._execute_service_logic(service.slug, payload)
            response_status = 200
        except Exception as e:
            logger.error(f"Service execution error for {service.slug}: {e}")
            raise
        
        # 4. Deduct credits
        if subscription:
            subscription.credits_remaining -= credits_needed
        user.credits_used += credits_needed
        
        if subscription:
            credits_after = float(subscription.credits_remaining)
        else:
            credits_after = float(user.total_credits - user.credits_used)
        user_credits_after = float(user.total_credits - user.credits_used)
        
        # 5. Log usage
        response_time_ms = int((time.time() - start_time) * 1000)
        usage_log = ApiUsageLog(
            user_id=user.id,
            api_key_id=api_key.id,
            service_id=service.id,
            subscription_id=subscription.id if subscription else None,
            endpoint_type=service.slug,
            request_params=payload,
            response_status=response_status,
            response_time_ms=response_time_ms,
            data_source=result.get("data_source", "db"),
            credits_deducted=credits_needed,
            credits_before=Decimal(str(credits_before)),
            credits_after=Decimal(str(credits_after)),
            success=True  # Only successful calls reach here
        )
        self.db.add(usage_log)
        
        # Update API key last used
        api_key.last_used_at = datetime.utcnow()
        
        await self.db.commit()
        
        # 6. Broadcast to WebSocket
        try:
            # Broadcast to user
            await manager.send_personal_message(
                create_api_call_event(
                    user_id=user.id,
                    service_id=service.id,
                    service_name=service.name,
                    api_key_id=api_key.id,
                    credits_deducted=float(credits_needed),
                    credits_before=credits_before,
                    credits_after=credits_after,
                    response_status=response_status,
                    response_time_ms=response_time_ms
                ),
                user.id
            )
            
            # Broadcast credit balance update
            await manager.send_personal_message(
                create_credit_balance_update_event(
                    user_id=user.id,
                    total_credits=float(user.total_credits),
                    credits_used=float(user.credits_used),
                    credits_remaining=user_credits_after
                ),
                user.id
            )
            
            # Broadcast to admin
            await manager.broadcast_to_admin(
                create_api_call_event(
                    user_id=user.id,
                    service_id=service.id,
                    service_name=service.name,
                    api_key_id=api_key.id,
                    credits_deducted=float(credits_needed),
                    credits_before=credits_before,
                    credits_after=credits_after,
                    response_status=response_status,
                    response_time_ms=response_time_ms
                )
            )
        except Exception as e:
            logger.error(f"Error broadcasting WebSocket event: {e}")
        
        # 7. Return result
        return result
    
    async def _execute_service_logic(self, service_slug: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute service-specific logic based on slug"""
        
        # Vehicle Screening Services
        if service_slug == "vehicle-rc-verification":
            reg_no = payload.get("reg_no") or payload.get("regNo")
            if not reg_no:
                raise ValueError("reg_no is required")
            result, data_source = await self.fallback_engine.fetch_rc_data(reg_no)
            if result is None:
                # Return 404 for data not found
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="RC data not found"
                )
            return {**result, "data_source": data_source}
        
        elif service_slug == "rc-to-mobile":
            reg_no = payload.get("reg_no") or payload.get("regNo")
            if not reg_no:
                raise ValueError("reg_no is required")
            return await self._fetch_rc_mobile(reg_no)
        
        elif service_slug == "rc-to-engine-chassis":
            reg_no = payload.get("reg_no") or payload.get("regNo")
            if not reg_no:
                raise ValueError("reg_no is required")
            result, data_source = await self.fallback_engine.fetch_rc_data(reg_no)
            if result is None:
                # Return 404 for data not found
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="RC data not found"
                )
            return {**result, "data_source": data_source}
        
        elif service_slug == "basic-vehicle-info":
            reg_no = payload.get("reg_no") or payload.get("regNo")
            if not reg_no:
                raise ValueError("reg_no is required")
            result, data_source = await self.fallback_engine.fetch_rc_data(reg_no)
            if result is None:
                # Return 404 for data not found
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="RC data not found"
                )
            # Return only basic fields
            data = result.get("data", {})
            basic_data = {
                "regNo": data.get("regNo"),
                "state": data.get("state"),
                "rto": data.get("rto"),
                "regDate": data.get("regDate"),
                "status": data.get("status"),
                "ownerName": data.get("ownerName"),
                "fatherName": data.get("fatherName"),
                "permanentAddress": data.get("permanentAddress"),
                "presentAddress": data.get("presentAddress"),
                "mobileNo": data.get("mobileNo"),
                "ownerSrNo": data.get("ownerSrNo"),
                "vehicleClass": data.get("vehicleClass"),
                "maker": data.get("maker"),
                "makerModel": data.get("makerModal"),
                "fuelType": data.get("fuelType")
            }
            return {
                "success": True,
                "status": 1,
                "data": basic_data,
                "message": "Vehicle owner details fetched successfully",
                "data_source": data_source
            }
        
        elif service_slug == "driving-licence":
            dl_no = payload.get("dl_no") or payload.get("dlNo")
            if not dl_no:
                raise ValueError("dl_no is required")
            result, data_source = await self.fallback_engine.fetch_licence_data(dl_no)
            if result is None:
                # Return 404 for data not found
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Licence data not found"
                )
            return {**result, "data_source": data_source}
        
        elif service_slug == "dl-to-challan":
            dl_no = payload.get("dl_no") or payload.get("dlNo")
            if not dl_no:
                raise ValueError("dl_no is required")
            return await self._fetch_dl_challan(dl_no)
        
        elif service_slug == "challan-detail":
            vehicle_no = payload.get("vehicle_no") or payload.get("vehicleNo")
            if not vehicle_no:
                raise ValueError("vehicle_no is required")
            result, data_source = await self.fallback_engine.fetch_challan_data(vehicle_no)
            if result is None:
                # Return 404 for data not found
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Challan data not found"
                )
            return {**result, "data_source": data_source}
        
        elif service_slug == "fuel-price-city":
            city = payload.get("city")
            if not city:
                raise ValueError("city is required")
            return await self._fetch_fuel_price(city=city)
        
        elif service_slug == "fuel-price-state":
            state = payload.get("state")
            if not state:
                raise ValueError("state is required")
            return await self._fetch_fuel_price(state=state)
        
        # KYC Status Services
        elif service_slug == "pan-verification":
            pan_number = payload.get("pan_number") or payload.get("panNumber")
            if not pan_number:
                raise ValueError("pan_number is required")
            return await self._fetch_pan_data(pan_number)
        
        elif service_slug == "aadhaar-to-pan":
            aadhaar_number = payload.get("aadhaar_number") or payload.get("aadhaarNumber")
            if not aadhaar_number:
                raise ValueError("aadhaar_number is required")
            return await self._fetch_pan_by_aadhaar(aadhaar_number)
        
        elif service_slug == "pan-to-aadhaar":
            pan_number = payload.get("pan_number") or payload.get("panNumber")
            if not pan_number:
                raise ValueError("pan_number is required")
            return await self._fetch_pan_data(pan_number)  # Same structure
        
        elif service_slug == "address-verification":
            aadhaar_no = payload.get("aadhaar_no") or payload.get("aadhaarNo")
            if not aadhaar_no:
                raise ValueError("aadhaar_no is required")
            return await self._fetch_address_verification(aadhaar_no)
        
        # Business Verification Services
        elif service_slug == "gst-verification" or service_slug == "gst-basic-details" or service_slug == "gst-address" or service_slug == "gst-aadhaar-status":
            gstin = payload.get("gstin") or payload.get("gstin")
            if not gstin:
                raise ValueError("gstin is required")
            return await self._fetch_gst_data(gstin)
        
        elif service_slug == "msme-verification":
            udyam_number = payload.get("udyam_number") or payload.get("udyamNumber")
            if not udyam_number:
                raise ValueError("udyam_number is required")
            return await self._fetch_msme_data(udyam_number)
        
        elif service_slug == "phone-to-udyam":
            phone_number = payload.get("phone_number") or payload.get("phoneNumber")
            if not phone_number:
                raise ValueError("phone_number is required")
            return await self._fetch_udyam_by_phone(phone_number)
        
        elif service_slug == "voter-id-verification":
            epic_number = payload.get("epic_number") or payload.get("epicNumber")
            if not epic_number:
                raise ValueError("epic_number is required")
            return await self._fetch_voter_id(epic_number)
        
        else:
            raise ValueError(f"Unknown service: {service_slug}")
    
    # Service-specific fetch methods
    async def _fetch_rc_mobile(self, reg_no: str) -> Dict[str, Any]:
        """Fetch RC to Mobile Number - tries RCMobileData first, then falls back to RCData"""
        # First, try RCMobileData table
        result = await self.db.execute(
            select(RCMobileData).where(RCMobileData.reg_no == reg_no)
        )
        data = result.scalar_one_or_none()
        
        if data and self._is_fresh(data.fetched_at, settings.RC_DATA_TTL_HOURS):
            return {
                "success": True,
                "regNo": data.reg_no,
                "status": 1,
                "data": {
                    "mobile_no": data.mobile_no,
                    "responseType": 1
                },
                "message": "Mobile Number fetched successfully",
                "dataType": 1,
                "data_source": data.data_source
            }
        
        # Fallback: Try to get mobile from RC data
        rc_result, rc_source = await self.fallback_engine.fetch_rc_data(reg_no)
        if rc_result and rc_result.get("data", {}).get("mobileNo"):
            mobile_no = rc_result["data"]["mobileNo"]
            return {
                "success": True,
                "regNo": reg_no,
                "status": 1,
                "data": {
                    "mobile_no": mobile_no,
                    "responseType": 1
                },
                "message": "Mobile Number fetched successfully",
                "dataType": 1,
                "data_source": rc_source
            }
        
        # If all fails, return 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RC mobile data not found"
        )
    
    async def _fetch_dl_challan(self, dl_no: str) -> Dict[str, Any]:
        """Fetch DL to Challan data"""
        result = await self.db.execute(
            select(DLChallanData).where(DLChallanData.dl_no == dl_no)
        )
        data = result.scalar_one_or_none()
        
        if data:
            return {
                "success": True,
                "status": 1,
                "data": {
                    "regNo": data.reg_no,
                    "state": data.state,
                    "rto": data.rto,
                    "regDate": data.reg_date,
                    "status": data.status,
                    "ownerName": data.owner_name,
                    "fatherName": data.father_name,
                    "permanentAddress": data.permanent_address,
                    "presentAddress": data.present_address,
                    "mobileNo": data.mobile_no,
                    "ownerSrNo": data.owner_sr_no,
                    "vehicleClass": data.vehicle_class,
                    "maker": data.maker,
                    "makerModel": data.maker_model,
                    "fuelType": data.fuel_type
                },
                "message": "Vehicle owner details fetched successfully",
                "data_source": data.data_source
            }
        
        # Try external API fallback (if configured)
        try:
            api_result = await self._try_external_api_fallback("dl_challan", {"dl_no": dl_no})
            if api_result:
                return api_result
        except Exception as e:
            logger.debug(f"External API fallback for DL Challan failed: {e}")
        
        # Return 404 for data not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DL challan data not found"
        )
    
    async def _fetch_fuel_price(self, city: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
        """Fetch Fuel Price by City or State"""
        query = select(FuelPriceData)
        if city:
            query = query.where(FuelPriceData.city == city)
        if state:
            query = query.where(FuelPriceData.state == state)
        query = query.where(FuelPriceData.date == datetime.now().date()).order_by(FuelPriceData.fetched_at.desc())
        
        result = await self.db.execute(query)
        data = result.scalar_one_or_none()
        
        if data:
            response_data = {
                "state": data.state,
                "fuel_prices": data.fuel_prices or []
            }
            if data.city:
                response_data["city"] = data.city
                response_data["date"] = data.date.isoformat() if data.date else None
            
            return {
                "code": "200",
                "message": "Fuel prices fetched successfully",
                "data": response_data,
                "source": data.source or "Indian Oil Corporation",
                "data_source": data.data_source
            }
        
        # Try external API fallback (if configured)
        try:
            api_params = {"city": city} if city else {"state": state}
            api_result = await self._try_external_api_fallback("fuel", api_params)
            if api_result:
                return api_result
        except Exception as e:
            logger.debug(f"External API fallback for Fuel Price failed: {e}")
        
        # Return 404 for data not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fuel price data not found"
        )
    
    async def _fetch_pan_data(self, pan_number: str) -> Dict[str, Any]:
        """Fetch PAN Verification data"""
        result = await self.db.execute(
            select(PANData).where(PANData.pan_number == pan_number)
        )
        data = result.scalar_one_or_none()
        
        if data:
            return {
                "api_category": "Know Your Customer (KYC)",
                "api_name": "PAN All in One",
                "billable": True,
                "txn_id": data.id,
                "message": "Success",
                "status": 1,
                "result": {
                    "pan_number": data.pan_number,
                    "full_name": data.full_name,
                    "full_name_split": data.full_name_split or [],
                    "masked_aadhaar": data.masked_aadhaar,
                    "address": data.address or {},
                    "email": data.email,
                    "tax": data.tax,
                    "phone_number": data.phone_number,
                    "gender": data.gender,
                    "dob": data.dob,
                    "aadhaar_linked": data.aadhaar_linked,
                    "category": data.category,
                    "less_info": data.less_info,
                    "is_director": data.is_director or {"found": "No", "info": []},
                    "is_sole_proprietor": data.is_sole_proprietor or {"found": "No", "info": []},
                    "fname": data.fname or "",
                    "din_info": data.din_info or {"din": "", "dinAllocationDate": "", "company_list": []}
                },
                "datetime": data.fetched_at.isoformat() if data.fetched_at else datetime.utcnow().isoformat(),
                "data_source": data.data_source
            }
        
        # Try external API fallback (if configured)
        try:
            api_result = await self._try_external_api_fallback("pan", {"pan_number": pan_number})
            if api_result:
                return api_result
        except Exception as e:
            logger.debug(f"External API fallback for PAN failed: {e}")
        
        # Return 404 for data not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PAN data not found"
        )
    
    async def _fetch_pan_by_aadhaar(self, aadhaar_number: str) -> Dict[str, Any]:
        """Fetch PAN by Aadhaar (same structure as PAN verification)"""
        result = await self.db.execute(
            select(PANData).where(PANData.aadhaar_number == aadhaar_number)
        )
        data = result.scalar_one_or_none()
        
        if data:
            return await self._fetch_pan_data(data.pan_number)
        
        # Try external API fallback (if configured)
        try:
            api_result = await self._try_external_api_fallback("pan", {"aadhaar_number": aadhaar_number})
            if api_result:
                return api_result
        except Exception as e:
            logger.debug(f"External API fallback for PAN by Aadhaar failed: {e}")
        
        # Return 404 for data not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PAN data not found for this Aadhaar"
        )
    
    async def _fetch_address_verification(self, aadhaar_no: str) -> Dict[str, Any]:
        """Fetch Address Verification data"""
        result = await self.db.execute(
            select(AddressVerificationData).where(AddressVerificationData.aadhaar_no == aadhaar_no)
        )
        data = result.scalar_one_or_none()
        
        if data:
            return {
                "status": 1,
                "message": "Aadhaar data fetched successfully",
                "success": True,
                "dataType": 1,
                "data": {
                    "dob": data.dob,
                    "category": data.category,
                    "fullName": data.full_name,
                    "firstName": data.first_name,
                    "middleName": data.middle_name,
                    "lastName": data.last_name,
                    "aadhaarNo": data.aadhaar_no,
                    "responseType": data.response_type
                },
                "data_source": data.data_source
            }
        
        # Try external API fallback (if configured)
        try:
            api_result = await self._try_external_api_fallback("address", {"aadhaar_no": aadhaar_no})
            if api_result:
                return api_result
        except Exception as e:
            logger.debug(f"External API fallback for Address Verification failed: {e}")
        
        # Return 404 for data not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address verification data not found"
        )
    
    async def _fetch_gst_data(self, gstin: str) -> Dict[str, Any]:
        """Fetch GST Verification data - checks DB first, then tries external APIs"""
        result = await self.db.execute(
            select(GSTData).where(GSTData.gstin == gstin)
        )
        data = result.scalar_one_or_none()
        
        if data:
            return {
                "api_category": "Know Your Business (KYB)",
                "api_name": "GST Verification (Advance)",
                "billable": True,
                "txn_id": data.id,
                "message": "Success",
                "status": 1,
                "result": {
                    "aggregate_turn_over": data.aggregate_turn_over,
                    "authorized_signatory": data.authorized_signatory or [],
                    "business_constitution": data.business_constitution,
                    "business_details": data.business_details or {},
                    "business_nature": data.business_nature or [],
                    "can_flag": data.can_flag,
                    "central_jurisdiction": data.central_jurisdiction,
                    "compliance_rating": data.compliance_rating,
                    "current_registration_status": data.current_registration_status,
                    "filing_status": data.filing_status or [],
                    "gstin": data.gstin,
                    "is_field_visit_conducted": data.is_field_visit_conducted,
                    "legal_name": data.legal_name,
                    "mandate_e_invoice": data.mandate_e_invoice,
                    "other_business_address": data.other_business_address or {},
                    "primary_business_address": data.primary_business_address or {},
                    "register_cancellation_date": data.register_cancellation_date,
                    "register_date": data.register_date,
                    "state_jurisdiction": data.state_jurisdiction,
                    "tax_payer_type": data.tax_payer_type,
                    "trade_name": data.trade_name,
                    "gross_total_income": data.gross_total_income,
                    "gross_total_income_financial_year": data.gross_total_income_financial_year
                },
                "datetime": data.fetched_at.isoformat() if data.fetched_at else datetime.utcnow().isoformat(),
                "data_source": data.data_source
            }
        
        # Try external API fallback (if configured)
        try:
            api_result = await self._try_external_api_fallback("gst", {"gstin": gstin})
            if api_result:
                return api_result
        except Exception as e:
            logger.debug(f"External API fallback for GST failed: {e}")
        
        # Return 404 for data not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GST data not found"
        )
    
    async def _fetch_msme_data(self, udyam_number: str) -> Dict[str, Any]:
        """Fetch MSME Verification data"""
        result = await self.db.execute(
            select(MSMEData).where(MSMEData.udyam_number == udyam_number)
        )
        data = result.scalar_one_or_none()
        
        if data:
            return {
                "api_category": "Know Your Business (KYB)",
                "api_name": "MSME",
                "billable": True,
                "txn_id": data.id,
                "message": "Record Found Successfully",
                "status": 1,
                "result": {
                    "enterprise_name": data.enterprise_name,
                    "organisation_type": data.organisation_type,
                    "service_type": data.service_type,
                    "gender": data.gender,
                    "social_category": data.social_category,
                    "date_of_incorporation": data.date_of_incorporation,
                    "date_of_commencement": data.date_of_commencement,
                    "address": data.address or {},
                    "mobile": data.mobile,
                    "email": data.email,
                    "plant_details": data.plant_details or [],
                    "enterprise_type": data.enterprise_type or [],
                    "nic_code": data.nic_code or [],
                    "dic": data.dic,
                    "msme-dfo": data.msme_dfo,
                    "date_of_udyam_registeration": data.date_of_udyam_registeration
                },
                "datetime": data.fetched_at.isoformat() if data.fetched_at else datetime.utcnow().isoformat(),
                "data_source": data.data_source
            }
        
        # Try external API fallback (if configured)
        try:
            api_result = await self._try_external_api_fallback("msme", {"udyam_number": udyam_number})
            if api_result:
                return api_result
        except Exception as e:
            logger.debug(f"External API fallback for MSME failed: {e}")
        
        # Return 404 for data not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MSME data not found"
        )
    
    async def _fetch_udyam_by_phone(self, phone_number: str) -> Dict[str, Any]:
        """Fetch Udyam by Phone Number"""
        result = await self.db.execute(
            select(UdyamData).where(UdyamData.phone_number == phone_number)
        )
        data = result.scalar_one_or_none()
        
        if data:
            return {
                "code": "1010",
                "message": "Udyam details fetched successfully.",
                "udyam_details": [{
                    "udyam_number": data.udyam_number,
                    "enterprise_name": data.enterprise_name
                }],
                "data_source": data.data_source
            }
        
        # Try external API fallback (if configured)
        try:
            api_result = await self._try_external_api_fallback("udyam", {"phone_number": phone_number})
            if api_result:
                return api_result
        except Exception as e:
            logger.debug(f"External API fallback for Udyam failed: {e}")
        
        # Return 404 for data not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Udyam data not found"
        )
    
    async def _fetch_voter_id(self, epic_number: str) -> Dict[str, Any]:
        """Fetch Voter ID Verification data"""
        result = await self.db.execute(
            select(VoterIDData).where(VoterIDData.epic_number == epic_number)
        )
        data = result.scalar_one_or_none()
        
        if data:
            return {
                "status": 200,
                "message": "Submitted successfully",
                "data": {
                    "epic_number": data.epic_number,
                    "status": data.status,
                    "name": data.name,
                    "name_in_regional_lang": data.name_in_regional_lang,
                    "age": data.age,
                    "relation_type": data.relation_type,
                    "relation_name": data.relation_name,
                    "relation_name_in_regional_lang": data.relation_name_in_regional_lang,
                    "father_name": data.father_name,
                    "dob": data.dob,
                    "gender": data.gender,
                    "state": data.state,
                    "assembly_constituency_number": data.assembly_constituency_number,
                    "assembly_constituency": data.assembly_constituency,
                    "parliamentary_constituency_number": data.parliamentary_constituency_number,
                    "parliamentary_constituency": data.parliamentary_constituency,
                    "part_number": data.part_number,
                    "part_name": data.part_name,
                    "serial_number": data.serial_number,
                    "polling_station": data.polling_station,
                    "address": data.address,
                    "photo": data.photo,
                    "split_address": data.split_address or {},
                    "urn": data.urn
                },
                "data_source": data.data_source
            }
        
        # Try external API fallback (if configured)
        try:
            api_result = await self._try_external_api_fallback("voter", {"epic_number": epic_number})
            if api_result:
                return api_result
        except Exception as e:
            logger.debug(f"External API fallback for Voter ID failed: {e}")
        
        # Return 404 for data not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voter ID data not found"
        )
    
    async def _try_external_api_fallback(self, api_type: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Try to fetch data from external APIs as fallback
        This is a generic fallback mechanism for services that don't have dedicated fallback logic
        """
        try:
            # Use the fallback engine's parallel API call mechanism
            api_result = await self.fallback_engine._parallel_api_call(api_type, params)
            if api_result and api_result[0]:
                # TODO: Store the result in appropriate database table
                logger.info(f"Got {api_type} data from external API: {api_result[1]}")
                return api_result[0]
        except Exception as e:
            logger.debug(f"External API fallback failed for {api_type}: {e}")
        return None
    
    def _is_fresh(self, fetched_at: datetime, ttl_hours: int) -> bool:
        """Check if data is fresh based on TTL"""
        if fetched_at is None:
            return False
        try:
            if fetched_at.tzinfo is not None:
                now = datetime.utcnow().replace(tzinfo=None)
                fetched = fetched_at.replace(tzinfo=None)
            else:
                now = datetime.utcnow()
                fetched = fetched_at
            age = now - fetched
            return age < timedelta(hours=ttl_hours)
        except Exception as e:
            logger.error(f"Error checking freshness: {str(e)}")
            return False

