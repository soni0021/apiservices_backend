from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid


class MSMEData(Base):
    __tablename__ = "msme_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    udyam_number = Column(String, unique=True, nullable=False, index=True)
    enterprise_name = Column(String, nullable=True, index=True)
    organisation_type = Column(String, nullable=True)
    service_type = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    social_category = Column(String, nullable=True)
    date_of_incorporation = Column(String, nullable=True)
    date_of_commencement = Column(String, nullable=True)
    address = Column(JSON, nullable=True)  # {flat_no, building, village, block, street, district, city, state, pin}
    mobile = Column(String, nullable=True)
    email = Column(String, nullable=True)
    plant_details = Column(JSON, nullable=True)  # Array of plant info
    enterprise_type = Column(JSON, nullable=True)  # Array with classification_year, enterprise_type, classification_date
    nic_code = Column(JSON, nullable=True)  # Array with nic_2_digit, nic_4_digit, nic_5_digit, activity, date
    dic = Column(String, nullable=True)
    msme_dfo = Column(String, nullable=True)
    date_of_udyam_registeration = Column(String, nullable=True)
    data_source = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

