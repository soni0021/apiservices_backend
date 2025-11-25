"""
Script to seed dummy data for testing
Run with: python -m app.scripts.seed_dummy_data
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole, UserStatus
from app.models.api_key import ApiKey, ApiKeyStatus
from app.models.rc_data import RCData
from app.models.rc_mobile_data import RCMobileData
from app.models.licence_data import LicenceData, LicenceCoverage
from app.models.challan_data import ChallanData, ChallanRecord, ChallanOffence
from app.models.dl_challan_data import DLChallanData
from app.models.pan_data import PANData
from app.models.address_verification_data import AddressVerificationData
from app.models.gst_data import GSTData
from app.models.msme_data import MSMEData
from app.models.udyam_data import UdyamData
from app.models.voter_id_data import VoterIDData
from app.models.fuel_price_data import FuelPriceData
from app.core.security import get_password_hash, generate_api_key, encrypt_api_key
from datetime import datetime, timedelta, date
from sqlalchemy import select


async def seed_data():
    """Seed dummy data"""
    print("Seeding dummy data...")
    
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        print("Checking for existing users...")
        # Check if admin user exists
        admin_result = await db.execute(select(User).where(User.email == "admin@example.com"))
        admin_user = admin_result.scalar_one_or_none()
        
        if not admin_user:
        print("Creating admin user...")
        admin_user = User(
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            full_name="Admin User",
            phone="+91 9876543210",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE
        )
        db.add(admin_user)
        await db.flush()
        else:
            print("Admin user already exists, skipping...")
        
        # Check if client user exists
        client_result = await db.execute(select(User).where(User.email == "client@example.com"))
        client_user = client_result.scalar_one_or_none()
        
        if not client_user:
        print("Creating client user...")
        client_user = User(
            email="client@example.com",
            password_hash=get_password_hash("client123"),
            full_name="Client User",
            phone="+91 9876543211",
            role=UserRole.CLIENT,
            status=UserStatus.ACTIVE
        )
        db.add(client_user)
        await db.flush()
        else:
            print("Client user already exists, skipping...")
        
        print("Checking for existing API key...")
        # Check if API key exists for client
        api_key_result = await db.execute(
            select(ApiKey).where(ApiKey.user_id == client_user.id, ApiKey.name == "Test API Key")
        )
        existing_key = api_key_result.scalar_one_or_none()
        
        if not existing_key:
        print("Creating API key for client...")
            # Create API key for client with all services access
        full_key, key_hash, key_prefix = generate_api_key("sk_live")
            encrypted_key = encrypt_api_key(full_key)
        api_key = ApiKey(
            user_id=client_user.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Test API Key",
                status=ApiKeyStatus.ACTIVE,
                allowed_services=["*"],  # All services access
                encrypted_key=encrypted_key
        )
        db.add(api_key)
        await db.flush()
        print(f"API Key created: {full_key}")
        print("⚠️  SAVE THIS KEY - It won't be shown again!")
        else:
            print("API key already exists, skipping...")
        
        print("Checking for existing RC data...")
        # Check if RC data exists
        rc_result = await db.execute(select(RCData).where(RCData.reg_no == "TR02AC1234"))
        existing_rc = rc_result.scalar_one_or_none()
        
        if not existing_rc:
        print("Creating dummy RC data...")
        # Create dummy RC data
        rc_data = RCData(
            reg_no="TR02AC1234",
            vi_status=1,
            status="ACTIVE",
            state="TR",
            rto="WEST TRIPURA JTC, Tripura",
            rto_code="TR-01",
            reg_date="2020-02-16",
            chassis_no="CAT76XX001C6P1XXXX",
            engine_no="LKJD05PXX54XXXX",
            vehicle_class="Goods Carrier(MGV)",
            vehicle_category="Goods Carrier(MGV)",
            vehicle_color="BRICK_RED",
            maker="TATA MOTORS LTD",
            maker_modal="910 LPK FGD256VGT 582B6N6",
            body_type_desc="TIPPER BODY",
            fuel_type="DIESEL",
            fuel_norms="BHARAT STAGE VI",
            owner_name="AJAY KUMAR",
            father_name="RAM KUMAR",
            permanent_address="JYOTI HEIGHTS, ANDHERI West Tripura Tripura 1719XX",
            present_address="JYOTI HEIGHTS, ANDHERI West Tripura Tripura 1719XX",
            mobile_no="9876543210",
            owner_sr_no=1,
            fitness_upto="2025-08-05",
            tax_upto="20-Jan-2025",
            ins_company="The New India Assurance Company Limited",
            ins_upto="2025-01-20",
            policy_no="5480008458560002XXXX",
            manufactured_month_year="12/2020",
            unladen_weight=4140,
            vehicle_gross_weight=9600,
            no_cylinders=4,
            cubic_cap=3300,
            no_of_seats=2,
            sleeper_cap=0,
            stand_cap=0,
            wheel_base=2775,
            financer_details="CIFCL",
            permit_no="TR2024-CG-05XXB",
            permit_issue_date="2024-01-25",
            permit_from="2024-01-25",
            permit_upto="2024-01-25",
            status_on="2024-07-30",
            data_source="db",
            fetched_at=datetime.utcnow()
        )
        db.add(rc_data)
        else:
            print("RC data already exists, skipping...")
        
        print("Checking for existing Licence data...")
        licence_result = await db.execute(select(LicenceData).where(LicenceData.dl_no == "GJ0520210012345"))
        existing_licence = licence_result.scalar_one_or_none()
        
        if not existing_licence:
        print("Creating dummy Licence data...")
        # Create dummy Licence data
        licence_data = LicenceData(
            dl_no="GJ0520210012345",
            error_cd=1,
            db_loc="database",
            bio_bio_id="2XXXX6AXXXXXJAXXX",
            bio_gender=1,
            bio_gender_desc="Male",
            bio_blood_group_name="B+",
            bio_citizen="IND",
            bio_first_name="RAJESH",
            bio_last_name="KUMAR",
            bio_full_name="RAJESH KUMAR",
            bio_nat_name="RAJESH KUMAR",
            bio_dependent_relation="F",
            bio_swd_full_name="RAM KUMAR",
            bio_perm_add1="123 MAIN STREET",
            bio_perm_add2="SURAT",
            bio_perm_add3="GUJARAT 395001",
            bio_temp_add1="123 MAIN STREET",
            bio_temp_add2="SURAT",
            bio_temp_add3="GUJARAT 395001",
            bio_dob="15-Nov-1996",
            bio_endorsement_no="GJ05/AXX/000XXXX/2021",
            bio_endorse_dt="15-Dec-2021",
            bio_photo_url="https://example.com/photo.jpg",
            bio_signature_url="https://example.com/signature.jpg",
            dl_status="Active",
            dl_issue_dt="17-Jul-2021",
            dl_nt_valdfr_dt="17-Jul-2021",
            dl_nt_valdto_dt="16-Jul-2041",
            dl_remarks="",
            ola_code="GJ05",
            ola_name="RTO,SURAT",
            state_cd="GJ",
            rto_code="GJ05",
            om_rto_fullname="RTO,SURAT",
            om_office_townname="SURAT",
            data_source="db",
            fetched_at=datetime.utcnow()
        )
        db.add(licence_data)
        await db.flush()
        
        # Add licence coverage
        coverage = LicenceCoverage(
            licence_id=licence_data.id,
            dl_no=licence_data.dl_no,
            cov_cd=4,
            cov_desc="LIGHT MOTOR VEHICLE",
            cov_abbrv="LMV",
            cov_status="A",
            vec_catg="NT",
            issue_dt="17-Jul-2021",
            endorse_dt="17-Jul-2021",
            ola_name="RTO,SURAT"
        )
        db.add(coverage)
        else:
            print("Licence data already exists, skipping...")
        
        print("Checking for existing Challan data...")
        challan_result = await db.execute(select(ChallanData).where(ChallanData.vehicle_no == "UP44BD0599"))
        existing_challan = challan_result.scalar_one_or_none()
        
        if not existing_challan:
        print("Creating dummy Challan data...")
        # Create dummy Challan data
        challan_data = ChallanData(
            vehicle_no="UP44BD0599",
            total_paid_count=1,
            total_pending_count=2,
            total_physical_court_count=1,
            total_virtual_court_count=0,
            data_source="db",
            fetched_at=datetime.utcnow()
        )
        db.add(challan_data)
        await db.flush()
        
        # Add challan record
        challan_record = ChallanRecord(
            challan_data_id=challan_data.id,
            reg_no="UP44BD0599",
            violator_name="SURESH KUMAR",
            dl_rc_no="UP44BD0599",
            challan_no="UP235845240813192709",
            challan_date="13-Aug-2024 19:27",
            challan_amount=1000,
            challan_status="Paid",
            challan_payment_date="15-Aug-2024",
            transaction_id="TXN123456789",
            state="UP",
            date="12-Sep-2024",
            dpt_cd=1,
            rto_cd=1191,
            court_name="CJM PRAYAGRAJ",
            court_address="prayagraj",
            sent_to_court_on="28-Aug-2024 11:54",
            designation="SI",
            traffic_police=1,
            vehicle_impound="No",
            virtual_court_status=1,
            court_status=1,
            valid_contact_no=1,
            office_name="Prayagraj",
            area_name="BAH",
            office_text="Prayagraj - BAH",
            payment_eligible=2,
            status_txt="Challan paid successfully",
            payment_gateway=1,
            physical_challan=0
        )
        db.add(challan_record)
        await db.flush()
        
        # Add offence
        offence = ChallanOffence(
            challan_record_id=challan_record.id,
            offence_name="Driving Two-wheeled without helmets",
            mva="Section 194 D of MVA 1988 RW section 129 of CMVA",
            penalty=1000
        )
        db.add(offence)
        else:
            print("Challan data already exists, skipping...")
        
        print("Checking for existing RC Mobile data...")
        rc_mobile_result = await db.execute(select(RCMobileData).where(RCMobileData.reg_no == "TR02AC1234"))
        existing_rc_mobile = rc_mobile_result.scalar_one_or_none()
        
        if not existing_rc_mobile:
            print("Creating dummy RC Mobile data...")
            # Create dummy RC Mobile data
            rc_mobile_data = RCMobileData(
            reg_no="TR02AC1234",
            mobile_no="9876543210",
            data_source="db",
            fetched_at=datetime.utcnow()
            )
            db.add(rc_mobile_data)
        else:
            print("RC Mobile data already exists, skipping...")
        
        print("Checking for existing PAN data...")
        pan_result = await db.execute(select(PANData).where(PANData.pan_number == "ABCDE1234F"))
        existing_pan = pan_result.scalar_one_or_none()
        
        if not existing_pan:
            print("Creating dummy PAN data...")
            # Create dummy PAN data (matching test input "ABCDE1234F")
            pan_data = PANData(
            pan_number="ABCDE1234F",
            aadhaar_number="123456789012",
            full_name="RAJESH KUMAR",
            full_name_split=["RAJESH", "KUMAR"],
            masked_aadhaar="1234****9012",
            address={
                "line_1": "123 MAIN STREET",
                "line_2": "ANDHERI",
                "street_name": "MAIN STREET",
                "zip": "400053",
                "city": "MUMBAI",
                "state": "MAHARASHTRA",
                "country": "INDIA",
                "full": "123 MAIN STREET, ANDHERI, MUMBAI, MAHARASHTRA 400053, INDIA"
            },
            email="rajesh.kumar@example.com",
            tax=True,
            phone_number="9876543210",
            gender="Male",
            dob="15-Nov-1990",
            aadhaar_linked=True,
            category="person",
            less_info=False,
            is_director={"found": "No", "info": []},
            is_sole_proprietor={"found": "No", "info": []},
            fname="RAJESH",
            din_info={"din": "", "dinAllocationDate": "", "company_list": []},
            data_source="db",
            fetched_at=datetime.utcnow()
            )
            db.add(pan_data)
        else:
            print("PAN data already exists, skipping...")
        
        print("Checking for existing GST data...")
        gst_result = await db.execute(select(GSTData).where(GSTData.gstin == "27ABCDE1234F1Z5"))
        existing_gst = gst_result.scalar_one_or_none()
        
        if not existing_gst:
            print("Creating dummy GST data...")
            # Create dummy GST data (matching test input "27ABCDE1234F1Z5")
            gst_data = GSTData(
            gstin="27ABCDE1234F1Z5",
            legal_name="ABC ENTERPRISES PRIVATE LIMITED",
            trade_name="ABC ENTERPRISES",
            business_constitution="Private Limited Company",
            aggregate_turn_over="50000000",
            authorized_signatory=["RAJESH KUMAR", "PRIYA SHARMA"],
            business_details={
                "bzsdtls": [
                    {"saccd": "1234", "sdes": "Manufacturing"}
                ]
            },
            business_nature=["Manufacturing", "Trading"],
            can_flag="N",
            central_jurisdiction="MUMBAI",
            compliance_rating="5",
            current_registration_status="Active",
            filing_status=[
                {"period": "2024-01", "status": "Filed"},
                {"period": "2024-02", "status": "Filed"}
            ],
            is_field_visit_conducted="No",
            mandate_e_invoice="No",
            other_business_address={},
            primary_business_address={
                "business_nature": "Manufacturing",
                "detailed_address": "123 INDUSTRIAL AREA, MUMBAI",
                "registered_address": "123 INDUSTRIAL AREA, MUMBAI, MAHARASHTRA 400053",
                "last_updated_date": "2024-01-15"
            },
            register_cancellation_date=None,
            register_date="2020-01-15",
            state_jurisdiction="MUMBAI",
            tax_payer_type="Regular",
            gross_total_income="50000000",
            gross_total_income_financial_year="2023-24",
            data_source="db",
            fetched_at=datetime.utcnow()
            )
            db.add(gst_data)
        else:
            print("GST data already exists, skipping...")
        
        print("Checking for existing MSME data...")
        msme_result = await db.execute(select(MSMEData).where(MSMEData.udyam_number == "UDYAM-MH-01-0001234"))
        existing_msme = msme_result.scalar_one_or_none()
        
        if not existing_msme:
            print("Creating dummy MSME data...")
            # Create dummy MSME data
            msme_data = MSMEData(
            udyam_number="UDYAM-MH-01-0001234",
            enterprise_name="ABC ENTERPRISES",
            organisation_type="Proprietorship",
            service_type="Manufacturing",
            gender="Male",
            social_category="General",
            date_of_incorporation="2020-01-15",
            date_of_commencement="2020-02-01",
            address={
                "flat_no": "123",
                "building": "INDUSTRIAL COMPLEX",
                "village": "",
                "block": "",
                "street": "INDUSTRIAL AREA",
                "district": "MUMBAI",
                "city": "MUMBAI",
                "state": "MAHARASHTRA",
                "pin": "400053"
            },
            mobile="9876543210",
            email="abc@enterprises.com",
            plant_details=[],
            enterprise_type=[
                {
                    "classification_year": "2024",
                    "enterprise_type": "Medium Enterprise",
                    "classification_date": "2024-01-01"
                }
            ],
            nic_code=[
                {
                    "nic_2_digit": "25",
                    "nic_4_digit": "2511",
                    "nic_5_digit": "25111",
                    "activity": "Manufacturing of motor vehicles",
                    "date": "2024-01-01"
                }
            ],
            dic="MUMBAI",
            msme_dfo="MUMBAI",
            date_of_udyam_registeration="2020-01-15",
            data_source="db",
            fetched_at=datetime.utcnow()
            )
            db.add(msme_data)
        else:
            print("MSME data already exists, skipping...")
        
        print("Checking for existing Udyam data...")
        udyam_result = await db.execute(select(UdyamData).where(UdyamData.phone_number == "9876543210"))
        existing_udyam = udyam_result.scalar_one_or_none()
        
        if not existing_udyam:
            print("Creating dummy Udyam data...")
            # Create dummy Udyam data (for phone-to-udyam service)
            udyam_data = UdyamData(
            phone_number="9876543210",
            udyam_number="UDYAM-MH-01-0001234",
            enterprise_name="ABC ENTERPRISES",
            data_source="db",
            fetched_at=datetime.utcnow()
            )
            db.add(udyam_data)
        else:
            print("Udyam data already exists, skipping...")
        
        print("Checking for existing Address Verification data...")
        address_result = await db.execute(select(AddressVerificationData).where(AddressVerificationData.aadhaar_no == "123456789012"))
        existing_address = address_result.scalar_one_or_none()
        
        if not existing_address:
            print("Creating dummy Address Verification data...")
            # Create dummy Address Verification data
            address_data = AddressVerificationData(
            aadhaar_no="123456789012",
            dob="15-Nov-1990",
            category="General",
            full_name="RAJESH KUMAR",
            first_name="RAJESH",
            middle_name="",
            last_name="KUMAR",
            response_type=1,
            data_source="db",
            fetched_at=datetime.utcnow()
            )
            db.add(address_data)
        else:
            print("Address Verification data already exists, skipping...")
        
        print("Checking for existing Voter ID data...")
        voter_result = await db.execute(select(VoterIDData).where(VoterIDData.epic_number == "ABC1234567"))
        existing_voter = voter_result.scalar_one_or_none()
        
        if not existing_voter:
            print("Creating dummy Voter ID data...")
            # Create dummy Voter ID data
            voter_data = VoterIDData(
            epic_number="ABC1234567",
            status="Active",
            name="RAJESH KUMAR",
            name_in_regional_lang="राजेश कुमार",
            age="34",
            relation_type="Son of",
            relation_name="RAM KUMAR",
            relation_name_in_regional_lang="राम कुमार",
            father_name="RAM KUMAR",
            dob="15-Nov-1990",
            gender="Male",
            state="MAHARASHTRA",
            assembly_constituency_number="123",
            assembly_constituency="ANDHERI WEST",
            parliamentary_constituency_number="24",
            parliamentary_constituency="MUMBAI NORTH",
            part_number="45",
            part_name="ANDHERI WEST",
            serial_number="1234",
            polling_station="PS 45, ANDHERI WEST",
            address="123 MAIN STREET, ANDHERI WEST, MUMBAI, MAHARASHTRA 400053",
            photo="https://example.com/voter_photo.jpg",
            split_address={
                "district": "MUMBAI",
                "state": "MAHARASHTRA",
                "city": "MUMBAI",
                "pincode": "400053",
                "country": "INDIA",
                "address_line": "123 MAIN STREET, ANDHERI WEST"
            },
            urn="123456789",
            data_source="db",
            fetched_at=datetime.utcnow()
            )
            db.add(voter_data)
        else:
            print("Voter ID data already exists, skipping...")
        
        print("Checking for existing Fuel Price data...")
        fuel_city_result = await db.execute(
            select(FuelPriceData).where(
                FuelPriceData.city == "MUMBAI",
                FuelPriceData.state == "MAHARASHTRA",
                FuelPriceData.date == date.today()
            )
        )
        existing_fuel_city = fuel_city_result.scalar_one_or_none()
        
        if not existing_fuel_city:
            print("Creating dummy Fuel Price data...")
            # Create dummy Fuel Price data for city
            fuel_price_city = FuelPriceData(
            city="MUMBAI",
            state="MAHARASHTRA",
            date=date.today(),
            source="Indian Oil Corporation",
            fuel_prices=[
                {"fuel_type": "Petrol", "price_per_litre": 96.72, "currency": "INR", "change_since_yesterday": 0.0},
                {"fuel_type": "Diesel", "price_per_litre": 89.62, "currency": "INR", "change_since_yesterday": 0.0}
            ],
            data_source="db",
            fetched_at=datetime.utcnow()
            )
            db.add(fuel_price_city)
            
            # Create dummy Fuel Price data for state
            fuel_price_state = FuelPriceData(
            city=None,
            state="MAHARASHTRA",
            date=date.today(),
            source="Indian Oil Corporation",
            fuel_prices=[
                {"fuel_type": "Petrol", "price_per_litre": 96.72, "currency": "INR", "change_since_yesterday": 0.0},
                {"fuel_type": "Diesel", "price_per_litre": 89.62, "currency": "INR", "change_since_yesterday": 0.0}
            ],
            data_source="db",
            fetched_at=datetime.utcnow()
            )
            db.add(fuel_price_state)
        else:
            print("Fuel Price data already exists, skipping...")
        
        print("Checking for existing DL Challan data...")
        dl_challan_result = await db.execute(select(DLChallanData).where(DLChallanData.dl_no == "GJ0520210012345"))
        existing_dl_challan = dl_challan_result.scalar_one_or_none()
        
        if not existing_dl_challan:
            print("Creating dummy DL Challan data...")
            # Create dummy DL Challan data
            dl_challan_data = DLChallanData(
            dl_no="GJ0520210012345",
            reg_no="GJ05AB1234",
            state="GUJARAT",
            rto="RTO,SURAT",
            reg_date="2020-01-15",
            status="ACTIVE",
            owner_name="RAJESH KUMAR",
            father_name="RAM KUMAR",
            permanent_address="123 MAIN STREET, SURAT, GUJARAT 395001",
            present_address="123 MAIN STREET, SURAT, GUJARAT 395001",
            mobile_no="9876543210",
            owner_sr_no=1,
            vehicle_class="LMV",
            maker="MARUTI SUZUKI",
            maker_model="SWIFT",
            fuel_type="PETROL",
            data_source="db",
            fetched_at=datetime.utcnow()
            )
            db.add(dl_challan_data)
        else:
            print("DL Challan data already exists, skipping...")
        
        await db.commit()
        print("\n✅ Dummy data seeded successfully!")
        print("\nLogin credentials:")
        print("Admin: admin@example.com / admin123")
        print("Client: client@example.com / client123")
        print(f"\nAPI Key: {full_key}")
        print("\n📋 Test Data Created:")
        print("  - RC: TR02AC1234")
        print("  - PAN: ABCDE1234F")
        print("  - GST: 27ABCDE1234F1Z5")
        print("  - MSME: UDYAM-MH-01-0001234")
        print("  - Phone (Udyam): 9876543210")
        print("  - Aadhaar (Address): 123456789012")
        print("  - Voter ID: ABC1234567")
        print("  - Fuel Price: MUMBAI / MAHARASHTRA")
        print("  - DL Challan: GJ0520210012345")


if __name__ == "__main__":
    asyncio.run(seed_data())

