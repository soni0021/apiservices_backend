from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.sql import func
from app.database import Base
import uuid


class AddressVerificationData(Base):
    __tablename__ = "address_verification_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    aadhaar_no = Column(String, nullable=False, index=True)
    dob = Column(String, nullable=True)
    category = Column(String, nullable=True)
    full_name = Column(String, nullable=True, index=True)
    first_name = Column(String, nullable=True)
    middle_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    response_type = Column(Integer, nullable=True)
    data_source = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

