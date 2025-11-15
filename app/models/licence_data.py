from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class LicenceData(Base):
    __tablename__ = "licence_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dl_no = Column(String, unique=True, nullable=False, index=True)
    
    # Response metadata
    error_cd = Column(Integer)
    db_loc = Column(String)
    
    # Bio data
    bio_bio_id = Column(String)
    bio_gender = Column(Integer)
    bio_gender_desc = Column(String)
    bio_blood_group_name = Column(String)
    bio_citizen = Column(String)
    bio_first_name = Column(String, index=True)
    bio_last_name = Column(String, index=True)
    bio_full_name = Column(String, index=True)
    bio_nat_name = Column(String)
    bio_dependent_relation = Column(String)
    bio_swd_full_name = Column(String)
    
    # Address fields
    bio_perm_add1 = Column(Text)
    bio_perm_add2 = Column(Text)
    bio_perm_add3 = Column(Text)
    bio_temp_add1 = Column(Text)
    bio_temp_add2 = Column(Text)
    bio_temp_add3 = Column(Text)
    
    # Personal details
    bio_dob = Column(String)
    bio_endorsement_no = Column(String)
    bio_endorse_dt = Column(String)
    
    # Photo and signature URLs
    bio_photo_url = Column(String)
    bio_signature_url = Column(String)
    
    # DL specific details
    dl_status = Column(String)
    dl_issue_dt = Column(String)
    dl_nt_valdfr_dt = Column(String)
    dl_nt_valdto_dt = Column(String)
    dl_remarks = Column(Text)
    
    # RTO details
    ola_code = Column(String)
    ola_name = Column(String)
    state_cd = Column(String)
    rto_code = Column(String)
    om_rto_fullname = Column(String)
    om_office_townname = Column(String)
    
    # Metadata
    data_source = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    coverages = relationship("LicenceCoverage", back_populates="licence", cascade="all, delete-orphan")


class LicenceCoverage(Base):
    __tablename__ = "licence_coverages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    licence_id = Column(String, ForeignKey("licence_data.id", ondelete="CASCADE"), nullable=False)
    dl_no = Column(String, nullable=False, index=True)
    
    # Coverage details
    cov_cd = Column(Integer)
    cov_desc = Column(String)
    cov_abbrv = Column(String)
    cov_status = Column(String)
    vec_catg = Column(String)
    
    # Dates
    issue_dt = Column(String)
    endorse_dt = Column(String)
    
    # RTO info
    ola_name = Column(String)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    licence = relationship("LicenceData", back_populates="coverages")

