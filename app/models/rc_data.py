from sqlalchemy import Column, String, DateTime, Integer, Text, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid


class RCData(Base):
    __tablename__ = "rc_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    reg_no = Column(String, unique=True, nullable=False, index=True)
    
    # Status fields
    vi_status = Column(Integer)
    status = Column(String)
    
    # Registration details
    state = Column(String)
    rto = Column(String)
    rto_code = Column(String)
    reg_date = Column(String)
    
    # Vehicle identifiers
    chassis_no = Column(String)
    engine_no = Column(String)
    
    # Vehicle specifications
    vehicle_class = Column(String)
    vehicle_category = Column(String)
    vehicle_color = Column(String)
    maker = Column(String)
    maker_modal = Column(String)
    body_type_desc = Column(String)
    fuel_type = Column(String)
    fuel_norms = Column(String)
    
    # Owner details
    owner_name = Column(String, index=True)
    father_name = Column(String)
    permanent_address = Column(Text)
    present_address = Column(Text)
    mobile_no = Column(String)
    owner_sr_no = Column(Integer)
    
    # Validity and compliance
    fitness_upto = Column(String)
    tax_upto = Column(String)
    
    # Insurance details
    ins_company = Column(String)
    ins_upto = Column(String)
    policy_no = Column(String)
    
    # PUC details
    puc_no = Column(String)
    puc_upto = Column(String)
    
    # Technical specifications
    manufactured_month_year = Column(String)
    unladen_weight = Column(Integer)
    vehicle_gross_weight = Column(Integer)
    no_cylinders = Column(Integer)
    cubic_cap = Column(Integer)
    no_of_seats = Column(Integer)
    sleeper_cap = Column(Integer)
    stand_cap = Column(Integer)
    wheel_base = Column(Integer)
    
    # Permit details
    national_permit_upto = Column(String)
    national_permit_no = Column(String)
    national_permit_issued_by = Column(String)
    permit_no = Column(String)
    permit_issue_date = Column(String)
    permit_from = Column(String)
    permit_upto = Column(String)
    permit_type = Column(String)
    
    # Finance details
    financer_details = Column(String)
    
    # Status and compliance
    blacklist_status = Column(String)
    noc_details = Column(String)
    status_on = Column(String)
    non_use_status = Column(String)
    non_use_from = Column(String)
    non_use_to = Column(String)
    
    # Additional fields from RC to Engine/Chassis API
    is_commercial = Column(String, nullable=True)  # boolean as string
    source = Column(String, nullable=True)
    own_json = Column(JSON, nullable=True)
    privahan_json = Column(JSON, nullable=True)
    
    # Metadata
    data_source = Column(String)  # db, api1, api2, api3
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

