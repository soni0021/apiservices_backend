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
from app.models.licence_data import LicenceData, LicenceCoverage
from app.models.challan_data import ChallanData, ChallanRecord, ChallanOffence
from app.core.security import get_password_hash, generate_api_key
from datetime import datetime, timedelta


async def seed_data():
    """Seed dummy data"""
    print("Seeding dummy data...")
    
    async with AsyncSessionLocal() as db:
        print("Creating admin user...")
        # Create admin user
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
        
        print("Creating client user...")
        # Create client user
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
        
        print("Creating API key for client...")
        # Create API key for client
        full_key, key_hash, key_prefix = generate_api_key("sk_live")
        api_key = ApiKey(
            user_id=client_user.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Test API Key",
            status=ApiKeyStatus.ACTIVE
        )
        db.add(api_key)
        await db.flush()
        
        print(f"API Key created: {full_key}")
        print("⚠️  SAVE THIS KEY - It won't be shown again!")
        
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
        
        await db.commit()
        print("\n✅ Dummy data seeded successfully!")
        print("\nLogin credentials:")
        print("Admin: admin@example.com / admin123")
        print("Client: client@example.com / client123")
        print(f"\nAPI Key: {full_key}")


if __name__ == "__main__":
    asyncio.run(seed_data())

