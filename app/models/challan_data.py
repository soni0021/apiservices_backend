from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class ChallanData(Base):
    __tablename__ = "challan_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_no = Column(String, nullable=False, index=True)
    
    # Summary counts
    total_paid_count = Column(Integer, default=0)
    total_pending_count = Column(Integer, default=0)
    total_physical_court_count = Column(Integer, default=0)
    total_virtual_court_count = Column(Integer, default=0)
    
    # Metadata
    data_source = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    records = relationship("ChallanRecord", back_populates="challan_data", cascade="all, delete-orphan")


class ChallanRecord(Base):
    __tablename__ = "challan_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    challan_data_id = Column(String, ForeignKey("challan_data.id", ondelete="CASCADE"), nullable=False)
    
    # Vehicle and violator details
    reg_no = Column(String, nullable=False, index=True)
    violator_name = Column(String, index=True)
    dl_rc_no = Column(String)
    
    # Challan details
    challan_no = Column(String, unique=True, nullable=False, index=True)
    challan_date = Column(String)
    challan_amount = Column(Integer)
    challan_status = Column(String)  # Paid, Pending, Virtual Court
    challan_payment_date = Column(String)
    transaction_id = Column(String)
    
    # Additional fields
    payment_source = Column(String)
    challan_url = Column(String)
    receipt_url = Column(String)
    payment_url = Column(String)
    state = Column(String)
    date = Column(String)
    
    # RTO and court details
    dpt_cd = Column(Integer)
    rto_cd = Column(Integer)
    court_name = Column(String)
    court_address = Column(Text)
    sent_to_court_on = Column(String)
    
    # Officer and location details
    designation = Column(String)
    traffic_police = Column(Integer)
    vehicle_impound = Column(String)
    office_name = Column(String)
    area_name = Column(String)
    office_text = Column(String)
    
    # Status information
    virtual_court_status = Column(Integer)
    court_status = Column(Integer)
    valid_contact_no = Column(Integer)
    payment_eligible = Column(Integer)
    status_txt = Column(Text)
    payment_gateway = Column(Integer)
    status_desc = Column(Text)
    physical_challan = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    challan_data = relationship("ChallanData", back_populates="records")
    offences = relationship("ChallanOffence", back_populates="challan_record", cascade="all, delete-orphan")


class ChallanOffence(Base):
    __tablename__ = "challan_offences"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    challan_record_id = Column(String, ForeignKey("challan_records.id", ondelete="CASCADE"), nullable=False)
    
    # Offence details
    offence_name = Column(Text)
    mva = Column(Text)  # Motor Vehicle Act section
    penalty = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    challan_record = relationship("ChallanRecord", back_populates="offences")

