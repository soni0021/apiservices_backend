"""
Script to seed marketplace data: industries, categories, services, and test data
Run with: python -m app.scripts.seed_marketplace_data
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import AsyncSessionLocal, init_db
from app.models.industry import Industry
from app.models.category import Category
from app.models.service import Service
from app.models.service_industry import ServiceIndustry
from app.models.user import User, UserRole, UserStatus
# Subscription model removed - using user_service_access instead
from app.models.transaction import Transaction, PaymentStatus
from app.models.api_key import ApiKey, ApiKeyStatus
from app.core.security import get_password_hash, generate_api_key
from app.models.rc_data import RCData
from app.models.rc_mobile_data import RCMobileData
from app.models.pan_data import PANData
from app.models.address_verification_data import AddressVerificationData
from app.models.fuel_price_data import FuelPriceData
from app.models.gst_data import GSTData
from app.models.msme_data import MSMEData
from app.models.udyam_data import UdyamData
from app.models.voter_id_data import VoterIDData
from app.models.dl_challan_data import DLChallanData


async def seed_marketplace():
    """Seed marketplace data"""
    print("Seeding marketplace data...")
    
    async with AsyncSessionLocal() as db:
        # 1. Create Industries
        print("Creating industries...")
        industries_data = [
            {"name": "Banking", "slug": "banking", "description": "Banking and financial services"},
            {"name": "Insurance", "slug": "insurance", "description": "Insurance companies and services"},
            {"name": "Automobile", "slug": "automobile", "description": "Automobile dealers and services"},
            {"name": "Legal Industry", "slug": "legal-industry", "description": "Legal firms and services"},
            {"name": "Fintech", "slug": "fintech", "description": "Financial technology companies"},
            {"name": "Mobility", "slug": "mobility", "description": "Taxi and mobility services"},
            {"name": "Logistic & Transport", "slug": "logistic-transport", "description": "Logistics and transportation"},
            {"name": "NBFC", "slug": "nbfc", "description": "Non-Banking Financial Companies"},
        ]
        
        industries = {}
        for ind_data in industries_data:
            industry = Industry(**ind_data)
            db.add(industry)
            await db.flush()
            industries[ind_data["slug"]] = industry
            print(f"  Created industry: {industry.name}")
        
        await db.commit()
        
        # 2. Create Categories
        print("Creating categories...")
        categories_data = [
            {"name": "KYC Status", "slug": "kyc-status", "description": "Know Your Customer verification APIs"},
            {"name": "Business Verification", "slug": "business-verification", "description": "Business and company verification APIs"},
            {"name": "Vehicle Screening", "slug": "vehicle-screening", "description": "Vehicle and driving license verification APIs"},
        ]
        
        categories = {}
        for cat_data in categories_data:
            category = Category(**cat_data)
            db.add(category)
            await db.flush()
            categories[cat_data["slug"]] = category
            print(f"  Created category: {category.name}")
        
        await db.commit()
        
        # 3. Create Services
        print("Creating services...")
        services_data = [
            # Vehicle Screening
            {"name": "Vehicle RC Verification", "slug": "vehicle-rc-verification", "category": "vehicle-screening", 
             "endpoint": "/api/v1/services/vehicle-rc-verification", "industries": ["banking", "insurance", "automobile", "logistic-transport", "nbfc"]},
            {"name": "RC to Mobile Number", "slug": "rc-to-mobile", "category": "vehicle-screening",
             "endpoint": "/api/v1/services/rc-to-mobile", "industries": ["banking", "insurance", "fintech"]},
            {"name": "RC to Engine and Chassis Number", "slug": "rc-to-engine-chassis", "category": "vehicle-screening",
             "endpoint": "/api/v1/services/rc-to-engine-chassis", "industries": ["automobile", "insurance"]},
            {"name": "Basic Vehicle Info", "slug": "basic-vehicle-info", "category": "vehicle-screening",
             "endpoint": "/api/v1/services/basic-vehicle-info", "industries": ["banking", "insurance", "automobile", "logistic-transport"]},
            {"name": "Driving License API", "slug": "driving-licence", "category": "kyc-status",
             "endpoint": "/api/v1/services/driving-licence", "industries": ["banking", "insurance", "mobility", "logistic-transport"]},
            {"name": "DL to Challan API", "slug": "dl-to-challan", "category": "vehicle-screening",
             "endpoint": "/api/v1/services/dl-to-challan", "industries": ["insurance", "legal-industry", "logistic-transport"]},
            {"name": "Challan Detail API", "slug": "challan-detail", "category": "vehicle-screening",
             "endpoint": "/api/v1/services/challan-detail", "industries": ["banking", "insurance", "legal-industry", "logistic-transport"]},
            {"name": "Fuel Price by City", "slug": "fuel-price-city", "category": "vehicle-screening",
             "endpoint": "/api/v1/services/fuel-price-city", "industries": ["automobile", "logistic-transport", "fintech"]},
            {"name": "Fuel Price by State", "slug": "fuel-price-state", "category": "vehicle-screening",
             "endpoint": "/api/v1/services/fuel-price-state", "industries": ["automobile", "logistic-transport", "fintech"]},
            
            # KYC Status
            {"name": "PAN Verification", "slug": "pan-verification", "category": "kyc-status",
             "endpoint": "/api/v1/services/pan-verification", "industries": ["banking", "insurance", "fintech", "nbfc"]},
            {"name": "Aadhaar to PAN", "slug": "aadhaar-to-pan", "category": "kyc-status",
             "endpoint": "/api/v1/services/aadhaar-to-pan", "industries": ["banking", "insurance", "fintech"]},
            {"name": "PAN to Aadhaar Verification", "slug": "pan-to-aadhaar", "category": "kyc-status",
             "endpoint": "/api/v1/services/pan-to-aadhaar", "industries": ["banking", "insurance", "fintech"]},
            {"name": "Address Verification", "slug": "address-verification", "category": "kyc-status",
             "endpoint": "/api/v1/services/address-verification", "industries": ["banking", "insurance", "logistic-transport"]},
            
            # Business Verification
            {"name": "GST Verification (Advance)", "slug": "gst-verification", "category": "business-verification",
             "endpoint": "/api/v1/services/gst-verification", "industries": ["banking", "insurance", "fintech", "logistic-transport"]},
            {"name": "GST Basic Details", "slug": "gst-basic-details", "category": "business-verification",
             "endpoint": "/api/v1/services/gst-basic-details", "industries": ["banking", "insurance", "fintech"]},
            {"name": "GST Address", "slug": "gst-address", "category": "business-verification",
             "endpoint": "/api/v1/services/gst-address", "industries": ["banking", "insurance", "logistic-transport"]},
            {"name": "GST Aadhaar Status", "slug": "gst-aadhaar-status", "category": "business-verification",
             "endpoint": "/api/v1/services/gst-aadhaar-status", "industries": ["banking", "insurance", "fintech"]},
            {"name": "MSME Verification", "slug": "msme-verification", "category": "business-verification",
             "endpoint": "/api/v1/services/msme-verification", "industries": ["banking", "insurance", "logistic-transport"]},
            {"name": "Udyam API", "slug": "phone-to-udyam", "category": "business-verification",
             "endpoint": "/api/v1/services/phone-to-udyam", "industries": ["banking", "insurance", "fintech"]},
            {"name": "Voter ID Verification", "slug": "voter-id-verification", "category": "kyc-status",
             "endpoint": "/api/v1/services/voter-id-verification", "industries": ["banking", "insurance", "fintech", "legal-industry"]},
        ]
        
        services = {}
        for svc_data in services_data:
            service = Service(
                name=svc_data["name"],
                slug=svc_data["slug"],
                category_id=categories[svc_data["category"]].id,
                description=f"{svc_data['name']} API service",
                endpoint_path=svc_data["endpoint"],
                price_per_call=Decimal("1.0"),
                is_active=True
            )
            db.add(service)
            await db.flush()
            services[svc_data["slug"]] = service
            
            # Link to industries
            for ind_slug in svc_data["industries"]:
                service_industry = ServiceIndustry(
                    service_id=service.id,
                    industry_id=industries[ind_slug].id
                )
                db.add(service_industry)
            
            print(f"  Created service: {service.name}")
        
        await db.commit()
        
        # 4. Create test users with subscriptions
        print("Creating test users with subscriptions...")
        
        # Get or create test client user
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == "client@example.com"))
        client_user = result.scalar_one_or_none()
        
        if not client_user:
            client_user = User(
                email="client@example.com",
                password_hash=get_password_hash("client123"),
                full_name="Test Client",
                phone="+91 9876543211",
                customer_name="Test Client Company",
                phone_number="+91 9876543211",
                address="123 Test Street, Mumbai",
                gst_number="27ABCDE1234F1Z5",
                pan_number="ABCDE1234F",
                role=UserRole.CLIENT,
                status=UserStatus.ACTIVE,
                total_credits=Decimal("400"),  # ₹2000 = 400 credits
                credits_used=Decimal("0")
            )
            db.add(client_user)
            await db.flush()
        
        # Create transaction for credit purchase
        transaction = Transaction(
            user_id=client_user.id,
            amount_paid=Decimal("2000"),
            credits_purchased=Decimal("400"),
            payment_method="test",
            payment_status=PaymentStatus.COMPLETED,
            transaction_id=f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        db.add(transaction)
        await db.commit()
        
        # Create subscriptions for some services
        print("Creating test subscriptions...")
        test_services = ["vehicle-rc-verification", "pan-verification", "gst-verification"]
        
        for svc_slug in test_services:
            service = services[svc_slug]
            subscription = Subscription(
                user_id=client_user.id,
                service_id=service.id,
                status=SubscriptionStatus.ACTIVE,
                credits_allocated=Decimal("100"),
                credits_remaining=Decimal("100"),
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            db.add(subscription)
            await db.flush()
            
            # Generate API key for this subscription
            full_key, key_hash, key_prefix = generate_api_key("sk_live")
            api_key = ApiKey(
                user_id=client_user.id,
                service_id=service.id,
                subscription_id=subscription.id,
                key_hash=key_hash,
                key_prefix=key_prefix,
                name=f"{service.name} API Key",
                status=ApiKeyStatus.ACTIVE
            )
            db.add(api_key)
            print(f"  Created subscription and API key for: {service.name}")
            print(f"    API Key: {full_key}")
        
        await db.commit()
        
        # 5. Create sample data for each service type
        print("Creating sample data...")
        
        # RC Mobile Data
        rc_mobile = RCMobileData(
            reg_no="TR02AC1234",
            mobile_no="9876543210",
            data_source="db"
        )
        db.add(rc_mobile)
        
        # PAN Data
        pan_data = PANData(
            pan_number="BHXXXXXXX0P",
            full_name="PRAVINBHAI M*******I J********A",
            full_name_split=["PRAVINBHAI", "M*******I", "J********A"],
            masked_aadhaar="XXXXXXXX5878",
            address={
                "line_1": "7**/7TH FLOOR",
                "line_2": "T*** ENCLAVE",
                "street_name": "S******** B.O",
                "zip": "395***",
                "city": "S********",
                "state": "G******",
                "country": "INDIA",
                "full": "7**/7TH FLOOR T*** ENCLAVE S******** B.O S******** G****** INDIA 395***"
            },
            email="zi***************en@gmail.com",
            tax=True,
            phone_number="76XXXXXX12",
            gender="M",
            dob="1968-06-01",
            aadhaar_linked=True,
            category="person",
            less_info=False,
            is_director={"found": "No", "info": []},
            is_sole_proprietor={"found": "Yes", "info": [{"gst": "24BHIPJ9020P1Z0", "aggregate_turn_over": "Slab: Rs. 0 to 40 lakhs", "status": "Active"}]},
            fname="",
            din_info={"din": "", "dinAllocationDate": "", "company_list": []},
            data_source="db"
        )
        db.add(pan_data)
        
        # Address Verification Data
        addr_verify = AddressVerificationData(
            aadhaar_no="8872XXXXXXXX9850",
            dob="1973-05-01",
            category="person",
            full_name="PRAMOD K***** S****",
            first_name="PRAMOD",
            middle_name="K*****",
            last_name="S****",
            response_type=1,
            data_source="db"
        )
        db.add(addr_verify)
        
        # Fuel Price Data (City)
        fuel_city = FuelPriceData(
            city="Mumbai",
            state="Maharashtra",
            date=datetime.now().date(),
            source="Indian Oil Corporation",
            fuel_prices=[
                {"fuel_type": "Petrol", "price_per_litre": 109.50, "currency": "INR", "change_since_yesterday": 0.25},
                {"fuel_type": "Diesel", "price_per_litre": 98.75, "currency": "INR", "change_since_yesterday": -0.10},
                {"fuel_type": "CNG", "price_per_kg": 85.00, "currency": "INR", "change_since_yesterday": 0.00},
                {"fuel_type": "LPG", "price_per_kg": 1100.00, "currency": "INR", "change_since_yesterday": 5.00}
            ],
            data_source="db"
        )
        db.add(fuel_city)
        
        # Fuel Price Data (State)
        fuel_state = FuelPriceData(
            city=None,
            state="Maharashtra",
            date=datetime.now().date(),
            source="Indian Oil Corporation",
            fuel_prices=[
                {"fuel_type": "Petrol", "price_per_litre": 109.50, "currency": "INR", "change_since_yesterday": 0.25},
                {"fuel_type": "Diesel", "price_per_litre": 98.75, "currency": "INR", "change_since_yesterday": -0.10},
                {"fuel_type": "CNG", "price_per_kg": 85.00, "currency": "INR", "change_since_yesterday": 0.00},
                {"fuel_type": "LPG", "price_per_kg": 1100.00, "currency": "INR", "change_since_yesterday": 5.00}
            ],
            data_source="db"
        )
        db.add(fuel_state)
        
        # GST Data
        gst_data = GSTData(
            gstin="07AB****27F1Z6",
            legal_name="AA** PA****** AD****** SE****** LLP",
            trade_name="AA** PA****** AD****** SE****** LLP",
            business_constitution="Limited Liability Partnership",
            aggregate_turn_over="Slab: Rs. 1.5 Cr. to 5 Cr.",
            authorized_signatory=["AK*** BA***L", "RA***H CH***RA"],
            business_details={
                "bzsdtls": [
                    {"saccd": "9982", "sdes": "Legal and accounting services"},
                    {"saccd": "9983", "sdes": "Other professional, technical and business services"}
                ]
            },
            business_nature=["Supplier of Services"],
            can_flag="NA",
            central_jurisdiction="State - CBIC,Zone - DELHI,Commissionerate - DELHI EAST,Division - NEHRU PLACE,Range - RANGE - ***",
            compliance_rating="NA",
            current_registration_status="Active",
            filing_status=[[{
                "fy": "2024-2025",
                "taxp": "March",
                "mof": "ONLINE",
                "dof": "11/04/2025",
                "rtntype": "GSTR1",
                "arn": "****",
                "status": "Filed"
            }]],
            is_field_visit_conducted="Yes",
            mandate_e_invoice="Yes",
            other_business_address={},
            primary_business_address={
                "business_nature": "Supplier of Services",
                "detailed_address": "NA",
                "last_updated_date": "NA",
                "registered_address": "Basement, D-1**, Defence Colony, New Delhi, South East Delhi, Delhi, 11****"
            },
            register_cancellation_date="",
            register_date="25/01/2023",
            state_jurisdiction="State - Delhi,Zone - Zone 9,Ward - Ward ** (Jurisdictional Office)",
            tax_payer_type="Regular",
            gross_total_income="Not Available",
            gross_total_income_financial_year="2023-2024",
            data_source="db"
        )
        db.add(gst_data)
        
        # MSME Data
        msme_data = MSMEData(
            udyam_number="UDYAM-HR-05-00*****36",
            enterprise_name="L***** B***",
            organisation_type="Proprietary",
            service_type="Services",
            gender="Female",
            social_category="OBC",
            date_of_incorporation="25/12/2014",
            date_of_commencement="25/12/2014",
            address={
                "flat_no": "FLAT NO ***",
                "building": "RAVI CLASSIC , S NO ***",
                "village": "BANER ROAD",
                "block": "NEAR D MART",
                "street": "BANER",
                "district": "PUNE",
                "city": "PUNE",
                "state": "MAHARASHTRA",
                "pin": "41****"
            },
            mobile="90*****902",
            email="lee***@gmail.com",
            plant_details=[{
                "unit_name": "LEENA BAKE",
                "flat": "FLAT NO ***",
                "building": "RAVI CLASSIC , S NO ***",
                "village": "BANER",
                "block": "",
                "road": "BANER ROAD , NEAR D MART",
                "district": "PUNE",
                "city": "PUNE",
                "state": "MAHARASHTRA",
                "pin": "41****"
            }],
            enterprise_type=[{
                "classification_year": "2022-23",
                "enterprise_type": "Micro",
                "classification_date": "01/02/2022"
            }],
            nic_code=[{
                "nic_2_digit": "10 - Manufacture of food products",
                "nic_4_digit": "1071 - Manufacture of bakery products",
                "nic_5_digit": "10711 - Manufacture of bread",
                "activity": "Manufacturing",
                "date": "07/12/2022"
            }],
            dic="PUNE",
            msme_dfo="MUMBAI",
            date_of_udyam_registeration="01/02/2022",
            data_source="db"
        )
        db.add(msme_data)
        
        # Udyam Data
        udyam_data = UdyamData(
            phone_number="9098765432",
            udyam_number="UDYAM-HR-05-00*****36",
            enterprise_name="H***Y O****E S******NS PVT *****",
            data_source="db"
        )
        db.add(udyam_data)
        
        # Voter ID Data
        voter_data = VoterIDData(
            epic_number="ABC****104",
            status="VALID",
            name="RAVI KUMAR",
            name_in_regional_lang="name in regional language",
            age="26",
            relation_type="FTHR",
            relation_name="RAJESH KUMAR",
            relation_name_in_regional_lang="name in regional language",
            father_name="RAJESH KUMAR",
            dob="",
            gender="Male",
            state="GUJARAT",
            assembly_constituency_number="107",
            assembly_constituency="BOTAD",
            parliamentary_constituency_number="15",
            parliamentary_constituency="BHAVNAGAR",
            part_number="291",
            part_name="ADATALA-2",
            serial_number="40",
            polling_station="V******an*** New P*****y School",
            address="V******an*** New P*****y School",
            photo=None,
            split_address={
                "district": ["BOTAD"],
                "state": [["GUJARAT"]],
                "city": ["BOTAD"],
                "pincode": "",
                "country": ["IN", "IND", "INDIA"],
                "address_line": "V******an*** New P*****y School"
            },
            urn="9******8-4b07-4**4-90ae-e*****077004",
            data_source="db"
        )
        db.add(voter_data)
        
        # DL Challan Data
        dl_challan = DLChallanData(
            dl_no="GJ0520210012345",
            reg_no="TR02ACXXXX",
            state="TR",
            rto="WEST TRIPURA JTC, Tripura",
            reg_date="2020-02-16",
            status="ACTIVE",
            owner_name="AJ*N*YA M*NI",
            father_name="R*GH*VA* M*NI",
            permanent_address="JY*T* H*IGH*S, AND*ER* West Tripura Tripura 1719XX",
            present_address="JY*T* H*IGH*S, AND*ER* West Tripura Tripura 1719XX",
            mobile_no=None,
            owner_sr_no=2,
            vehicle_class="Goods Carrier(MGV)",
            maker="TATA MOTORS LTD",
            maker_model="910 LPK FGD256VGT 582B6N6",
            fuel_type="DIESEL",
            data_source="db"
        )
        db.add(dl_challan)
        
        await db.commit()
        
        print("\n✅ Marketplace data seeded successfully!")
        print(f"\nCreated:")
        print(f"  - {len(industries)} Industries")
        print(f"  - {len(categories)} Categories")
        print(f"  - {len(services)} Services")
        print(f"  - Test subscriptions and API keys")
        print(f"  - Sample data for all service types")


if __name__ == "__main__":
    asyncio.run(seed_marketplace())

