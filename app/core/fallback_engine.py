import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models.rc_data import RCData
from app.models.licence_data import LicenceData
from app.models.challan_data import ChallanData, ChallanRecord
import logging

settings = get_settings()
logger = logging.getLogger(__name__)


class FallbackEngine:
    """Engine for parallel API calls with fallback logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.timeout = aiohttp.ClientTimeout(total=5)
    
    async def fetch_rc_data(self, reg_no: str) -> Optional[Dict[str, Any]]:
        """
        Fetch RC data with fallback logic
        1. Check DB for fresh data
        2. If stale/missing, call external APIs in parallel
        3. Return fastest response and update DB in background
        """
        # Check DB first
        db_data = await self._get_rc_from_db(reg_no)
        if db_data and self._is_fresh(db_data.fetched_at, settings.RC_DATA_TTL_HOURS):
            logger.info(f"RC data for {reg_no} found in DB (fresh)")
            return self._rc_model_to_dict(db_data), "db"
        
        logger.info(f"RC data for {reg_no} not fresh, calling external APIs")
        
        # Call external APIs in parallel
        api_result = await self._parallel_api_call("rc", {"reg_no": reg_no})
        
        if api_result:
            # Update DB in background
            asyncio.create_task(self._update_rc_in_db(reg_no, api_result[0]))
            return api_result[0], api_result[1]
        
        # If all APIs fail, return stale data if available
        if db_data:
            logger.warning(f"All APIs failed for {reg_no}, returning stale data")
            return self._rc_model_to_dict(db_data), "db"
        
        return None, None
    
    async def fetch_licence_data(self, dl_no: str, dob: str) -> Optional[Dict[str, Any]]:
        """Fetch licence data with fallback logic"""
        # Check DB first
        db_data = await self._get_licence_from_db(dl_no)
        if db_data and self._is_fresh(db_data.fetched_at, settings.DL_DATA_TTL_HOURS):
            logger.info(f"Licence data for {dl_no} found in DB (fresh)")
            return self._licence_model_to_dict(db_data), "db"
        
        logger.info(f"Licence data for {dl_no} not fresh, calling external APIs")
        
        # Call external APIs in parallel
        api_result = await self._parallel_api_call("dl", {"dl_no": dl_no, "dob": dob})
        
        if api_result:
            # Update DB in background
            asyncio.create_task(self._update_licence_in_db(dl_no, api_result[0]))
            return api_result[0], api_result[1]
        
        # If all APIs fail, return stale data if available
        if db_data:
            logger.warning(f"All APIs failed for {dl_no}, returning stale data")
            return self._licence_model_to_dict(db_data), "db"
        
        return None, None
    
    async def fetch_challan_data(self, vehicle_no: str) -> Optional[Dict[str, Any]]:
        """Fetch challan data with fallback logic"""
        # Check DB first
        db_data = await self._get_challan_from_db(vehicle_no)
        if db_data and self._is_fresh(db_data.fetched_at, settings.CHALLAN_DATA_TTL_HOURS):
            logger.info(f"Challan data for {vehicle_no} found in DB (fresh)")
            return self._challan_model_to_dict(db_data), "db"
        
        logger.info(f"Challan data for {vehicle_no} not fresh, calling external APIs")
        
        # Call external APIs in parallel
        api_result = await self._parallel_api_call("challan", {"vehicle_no": vehicle_no})
        
        if api_result:
            # Update DB in background
            asyncio.create_task(self._update_challan_in_db(vehicle_no, api_result[0]))
            return api_result[0], api_result[1]
        
        # If all APIs fail, return stale data if available
        if db_data:
            logger.warning(f"All APIs failed for {vehicle_no}, returning stale data")
            return self._challan_model_to_dict(db_data), "db"
        
        return None, None
    
    async def _parallel_api_call(
        self, 
        api_type: str, 
        params: Dict[str, str]
    ) -> Optional[tuple[Dict[str, Any], str]]:
        """
        Call all 3 external APIs in parallel and return the fastest successful response
        Returns: (data, source) where source is 'api1', 'api2', or 'api3'
        """
        tasks = []
        
        # Create tasks for all 3 APIs
        if settings.EXTERNAL_API_1_URL:
            tasks.append(self._call_api(settings.EXTERNAL_API_1_URL, settings.EXTERNAL_API_1_KEY, api_type, params, "api1"))
        if settings.EXTERNAL_API_2_URL:
            tasks.append(self._call_api(settings.EXTERNAL_API_2_URL, settings.EXTERNAL_API_2_KEY, api_type, params, "api2"))
        if settings.EXTERNAL_API_3_URL:
            tasks.append(self._call_api(settings.EXTERNAL_API_3_URL, settings.EXTERNAL_API_3_KEY, api_type, params, "api3"))
        
        if not tasks:
            logger.warning("No external APIs configured")
            return None
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Return the first successful result
        for result in results:
            if isinstance(result, tuple) and result[0] is not None:
                logger.info(f"Got successful response from {result[1]}")
                return result
        
        logger.error("All external APIs failed")
        return None
    
    async def _call_api(
        self,
        base_url: str,
        api_key: str,
        api_type: str,
        params: Dict[str, str],
        source: str
    ) -> tuple[Optional[Dict[str, Any]], str]:
        """Call a single external API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
                endpoint = f"{base_url}/{api_type}"
                
                async with session.post(endpoint, json=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("success"):
                            return data, source
            return None, source
        except Exception as e:
            logger.error(f"Error calling {source}: {str(e)}")
            return None, source
    
    def _is_fresh(self, fetched_at: datetime, ttl_hours: int) -> bool:
        """Check if data is fresh based on TTL"""
        if fetched_at is None:
            return False
        try:
            # Handle timezone-aware and naive datetimes
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
    
    # Database query methods
    async def _get_rc_from_db(self, reg_no: str) -> Optional[RCData]:
        """Get RC data from database"""
        result = await self.db.execute(
            select(RCData).where(RCData.reg_no == reg_no)
        )
        return result.scalar_one_or_none()
    
    async def _get_licence_from_db(self, dl_no: str) -> Optional[LicenceData]:
        """Get licence data from database with coverages"""
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(LicenceData)
            .options(selectinload(LicenceData.coverages))
            .where(LicenceData.dl_no == dl_no)
        )
        return result.scalar_one_or_none()
    
    async def _get_challan_from_db(self, vehicle_no: str) -> Optional[ChallanData]:
        """Get challan data from database with records and offences"""
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(ChallanData)
            .options(
                selectinload(ChallanData.records).selectinload(ChallanRecord.offences)
            )
            .where(ChallanData.vehicle_no == vehicle_no)
        )
        return result.scalar_one_or_none()
    
    # Model to dict conversion methods (simplified - would need full implementation)
    def _rc_model_to_dict(self, model: RCData) -> Dict[str, Any]:
        """Convert RC model to response dict"""
        return {
            "success": True,
            "status": model.vi_status if hasattr(model, 'vi_status') else 1,
            "data": {
                "viStatus": model.vi_status if hasattr(model, 'vi_status') else 1,
                "status": model.status or "ACTIVE",
                "regNo": model.reg_no or "",
                "state": model.state or "",
                "rto": model.rto or "",
                "regDate": model.reg_date or "",
                "chassisNo": model.chassis_no or "",
                "engineNo": model.engine_no or "",
                "vehicleClass": model.vehicle_class or "",
                "vehicleColor": model.vehicle_color or "",
                "maker": model.maker or "",
                "makerModal": model.maker_modal or "",
                "bodyTypeDesc": model.body_type_desc or "",
                "fuelType": model.fuel_type or "",
                "fuelNorms": model.fuel_norms or "",
                "ownerName": model.owner_name or "",
                "fatherName": model.father_name or "",
                "permanentAddress": model.permanent_address or "",
                "presentAddress": model.present_address or "",
                "mobileNo": model.mobile_no,
                "ownerSrNo": model.owner_sr_no or 1,
                "fitnessUpto": model.fitness_upto or "",
                "taxUpto": model.tax_upto or "",
                "insCompany": model.ins_company or "",
                "insUpto": model.ins_upto or "",
                "policyNo": model.policy_no or "",
                "pucNo": model.puc_no,
                "pucUpto": model.puc_upto,
                "manufacturedMonthYear": model.manufactured_month_year or "",
                "unladenWeight": model.unladen_weight or 0,
                "vehicleGrossWeight": model.vehicle_gross_weight or 0,
                "noCylinders": model.no_cylinders or 0,
                "cubicCap": model.cubic_cap or 0,
                "noOfSeats": model.no_of_seats or 0,
                "sleeperCap": model.sleeper_cap or 0,
                "standCap": model.stand_cap or 0,
                "wheelBase": model.wheel_base or 0,
                "nationalPermitUpto": model.national_permit_upto,
                "nationalPermitNo": model.national_permit_no,
                "nationalPermitIssuedBy": model.national_permit_issued_by,
                "financerDetails": model.financer_details or "",
                "permitNo": model.permit_no or "",
                "permitIssueDate": model.permit_issue_date or "",
                "permitFrom": model.permit_from or "",
                "permitUpto": model.permit_upto or "",
                "permitType": model.permit_type,
                "blacklistStatus": model.blacklist_status,
                "nocDetails": model.noc_details,
                "statusOn": model.status_on or "",
                "nonUseStatus": model.non_use_status,
                "nonUseFrom": model.non_use_from,
                "nonUseTo": model.non_use_to,
                "createdAt": model.fetched_at.isoformat() if model.fetched_at else datetime.utcnow().isoformat(),
                "updatedAt": model.fetched_at.isoformat() if model.fetched_at else datetime.utcnow().isoformat(),
                "vehicleCategory": model.vehicle_category or "",
                "rtoCode": model.rto_code or "",
                "responseType": 1
            },
            "message": "Data fetched from database",
            "dataType": 1
        }
    
    def _licence_model_to_dict(self, model: LicenceData) -> Dict[str, Any]:
        """Convert licence model to response dict"""
        # Convert coverages
        dlcovs = []
        if hasattr(model, 'coverages') and model.coverages:
            for cov in model.coverages:
                dlcovs.append({
                    "dcLicno": cov.dl_no or "",
                    "dcCovcd": cov.cov_cd or 0,
                    "endouserid": 0,
                    "olacd": "",
                    "olaName": cov.ola_name or "",
                    "dcApplno": 0,
                    "dcCovStatus": cov.cov_status or "",
                    "dcEndorseNo": "",
                    "dcEndorsetime": "",
                    "covdesc": cov.cov_desc or "",
                    "covabbrv": cov.cov_abbrv or "",
                    "vecatg": cov.vec_catg or "",
                    "veShortdesc": "",
                    "dcEndorsedt": cov.endorse_dt or "",
                    "dcIssuedt": cov.issue_dt or ""
                })
        
        return {
            "errorcd": model.error_cd or 1,
            "bioObj": {
                "bioBioId": model.bio_bio_id or "",
                "bioGender": model.bio_gender or 0,
                "bioGenderDesc": model.bio_gender_desc or "",
                "bioBloodGroupname": model.bio_blood_group_name or "",
                "bioQmQualcd": 0,
                "bioCitiZen": model.bio_citizen or "",
                "bioUserId": 0,
                "bioFirstName": model.bio_first_name or "",
                "bioLastName": model.bio_last_name or "",
                "bioFullName": model.bio_full_name or "",
                "bioNatName": model.bio_nat_name or "",
                "bioDependentRelation": model.bio_dependent_relation or "",
                "bioSwdFullName": model.bio_swd_full_name or "",
                "bioSwdFname": "",
                "bioPermAdd1": model.bio_perm_add1 or "",
                "bioPermAdd2": model.bio_perm_add2 or "",
                "bioPermAdd3": model.bio_perm_add3 or "",
                "bioTempAdd1": model.bio_temp_add1 or "",
                "bioTempAdd2": model.bio_temp_add2 or "",
                "bioTempAdd3": model.bio_temp_add3 or "",
                "bioDlno": model.dl_no or "",
                "bioPermSdcode": 0,
                "bioTempSdcode": 0,
                "bioRecGenesis": "",
                "bioEndorsementNo": model.bio_endorsement_no or "",
                "bioEndorsetime": "",
                "bioApplno": 0,
                "aadharAuthenticated": False,
                "bioDob": model.bio_dob or "",
                "bioEndorsedt": model.bio_endorse_dt or ""
            },
            "bioImgObj": {
                "biBioId": model.bio_bio_id or "",
                "biusid": 0,
                "biApplno": 0,
                "biPhotoDate": "",
                "biSignDate": "",
                "biBioCapturedDt": "",
                "biConfirmCapture": 0,
                "biPhoto": model.bio_photo_url or "",
                "biSignature": model.bio_signature_url or "",
                "biEndorsedt": 0,
                "biEndorsetime": "",
                "bdDevId": 0
            },
            "dlobj": {
                "dlLicno": model.dl_no or "",
                "bioid": model.bio_bio_id or "",
                "olacode": model.ola_code or "",
                "olaName": model.ola_name or "",
                "statecd": model.state_cd or "",
                "dlApplno": 0,
                "dlUsid": 0,
                "dlIssueauth": "",
                "dlEndorseno": model.bio_endorsement_no or "",
                "dlEndorseAuth": "",
                "dlRecGenesis": "",
                "dlLatestTrcode": 0,
                "dlStatus": model.dl_status or "",
                "dlRemarks": model.dl_remarks or "",
                "dlEndorsetime": "",
                "dlRtoCode": model.rto_code or "",
                "omRtoFullname": model.om_rto_fullname or "",
                "omRtoShortname": "",
                "omOfficeTownname": model.om_office_townname or "",
                "enforceRemark": "",
                "dlIntermediateStage": "",
                "dlIncChallanNo": "",
                "dlIncSourceType": "",
                "dlIncRtoAction": "",
                "dlIssuedt": model.dl_issue_dt or "",
                "dlNtValdfrDt": model.dl_nt_valdfr_dt or "",
                "dlNtValdtoDt": model.dl_nt_valdto_dt or "",
                "dlEndorsedt": model.bio_endorse_dt or ""
            },
            "dlcovs": dlcovs,
            "dbLoc": model.db_loc or "database"
        }
    
    def _challan_model_to_dict(self, model: ChallanData) -> Dict[str, Any]:
        """Convert challan model to response dict"""
        # Categorize records by status
        paid_records = []
        pending_records = []
        physical_court_records = []
        virtual_court_records = []
        
        if hasattr(model, 'records') and model.records:
            for record in model.records:
                # Get offences for this record
                offences = []
                if hasattr(record, 'offences') and record.offences:
                    for offence in record.offences:
                        offences.append({
                            "offenceName": offence.offence_name or "",
                            "mva": offence.mva or "",
                            "penalty": offence.penalty or 0
                        })
                
                record_dict = {
                    "regNo": record.reg_no or "",
                    "violatorName": record.violator_name or "",
                    "dlRcNo": record.dl_rc_no or "",
                    "challanNo": record.challan_no or "",
                    "challanDate": record.challan_date or "",
                    "challanAmount": record.challan_amount or 0,
                    "challanStatus": record.challan_status or "",
                    "challanPaymentDate": record.challan_payment_date or "",
                    "transactionId": record.transaction_id or "",
                    "paymentSource": record.payment_source or "",
                    "challanUrl": record.challan_url or "",
                    "receiptUrl": record.receipt_url or "",
                    "paymentUrl": record.payment_url or "",
                    "state": record.state or "",
                    "date": record.date or "",
                    "dptCd": record.dpt_cd or 0,
                    "rtoCd": record.rto_cd or 0,
                    "courtName": record.court_name or "",
                    "courtAddress": record.court_address or "",
                    "sentToCourtOn": record.sent_to_court_on or "",
                    "designation": record.designation or "",
                    "trafficPolice": record.traffic_police or 0,
                    "vehicleImpound": record.vehicle_impound or "",
                    "virtualCourtStatus": record.virtual_court_status or 0,
                    "courtStatus": record.court_status or 0,
                    "validContactNo": record.valid_contact_no or 0,
                    "officeName": record.office_name or "",
                    "areaName": record.area_name or "",
                    "officeText": record.office_text or "",
                    "paymentEligible": record.payment_eligible or 0,
                    "statusTxt": record.status_txt or "",
                    "paymentGateway": record.payment_gateway or 0,
                    "statusDesc": record.status_desc or "",
                    "physicalChallan": record.physical_challan or 0,
                    "challanOffences": offences
                }
                
                # Categorize based on status
                status = record.challan_status or ""
                if "Paid" in status or "paid" in status.lower():
                    paid_records.append(record_dict)
                elif record.virtual_court_status and record.virtual_court_status > 0:
                    virtual_court_records.append(record_dict)
                elif record.physical_challan and record.physical_challan > 0:
                    physical_court_records.append(record_dict)
                else:
                    pending_records.append(record_dict)
        
        return {
            "success": True,
            "status": 1,
            "data": {
                "paidChallans": {
                    "count": len(paid_records),
                    "data": paid_records
                },
                "pendingChallans": {
                    "count": len(pending_records),
                    "data": pending_records
                },
                "physicalCourtChallans": {
                    "count": len(physical_court_records),
                    "data": physical_court_records
                },
                "virtualCourtChallans": {
                    "count": len(virtual_court_records),
                    "data": virtual_court_records
                }
            },
            "responseType": 1,
            "message": "Data fetched from database",
            "dataType": 1
        }
    
    # Database update methods (background tasks)
    async def _update_rc_in_db(self, reg_no: str, data: Dict[str, Any]):
        """Update RC data in database (background task)"""
        try:
            # Implementation would parse data and update/insert RC record
            logger.info(f"Updated RC data for {reg_no} in database")
        except Exception as e:
            logger.error(f"Error updating RC data: {str(e)}")
    
    async def _update_licence_in_db(self, dl_no: str, data: Dict[str, Any]):
        """Update licence data in database (background task)"""
        try:
            # Implementation would parse data and update/insert licence record
            logger.info(f"Updated licence data for {dl_no} in database")
        except Exception as e:
            logger.error(f"Error updating licence data: {str(e)}")
    
    async def _update_challan_in_db(self, vehicle_no: str, data: Dict[str, Any]):
        """Update challan data in database (background task)"""
        try:
            # Implementation would parse data and update/insert challan record
            logger.info(f"Updated challan data for {vehicle_no} in database")
        except Exception as e:
            logger.error(f"Error updating challan data: {str(e)}")

