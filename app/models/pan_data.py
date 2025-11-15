from sqlalchemy import Column, String, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid


class PANData(Base):
    __tablename__ = "pan_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pan_number = Column(String, unique=True, nullable=False, index=True)
    aadhaar_number = Column(String, nullable=True, index=True)  # For PAN to Aadhaar lookup
    full_name = Column(String, nullable=True, index=True)
    full_name_split = Column(JSON, nullable=True)  # Array of name parts
    masked_aadhaar = Column(String, nullable=True)
    address = Column(JSON, nullable=True)  # line_1, line_2, street_name, zip, city, state, country, full
    email = Column(String, nullable=True)
    tax = Column(Boolean, nullable=True)
    phone_number = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    dob = Column(String, nullable=True)
    aadhaar_linked = Column(Boolean, nullable=True)
    category = Column(String, nullable=True)  # person/company
    less_info = Column(Boolean, nullable=True)
    is_director = Column(JSON, nullable=True)  # {found, info}
    is_sole_proprietor = Column(JSON, nullable=True)  # {found, info}
    fname = Column(String, nullable=True)
    din_info = Column(JSON, nullable=True)  # {din, dinAllocationDate, company_list}
    data_source = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

