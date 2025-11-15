from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid


class VoterIDData(Base):
    __tablename__ = "voter_id_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    epic_number = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, nullable=True)
    name = Column(String, nullable=True, index=True)
    name_in_regional_lang = Column(String, nullable=True)
    age = Column(String, nullable=True)
    relation_type = Column(String, nullable=True)
    relation_name = Column(String, nullable=True)
    relation_name_in_regional_lang = Column(String, nullable=True)
    father_name = Column(String, nullable=True)
    dob = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    state = Column(String, nullable=True, index=True)
    assembly_constituency_number = Column(String, nullable=True)
    assembly_constituency = Column(String, nullable=True)
    parliamentary_constituency_number = Column(String, nullable=True)
    parliamentary_constituency = Column(String, nullable=True)
    part_number = Column(String, nullable=True)
    part_name = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    polling_station = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    photo = Column(String, nullable=True)
    split_address = Column(JSON, nullable=True)  # {district, state, city, pincode, country, address_line}
    urn = Column(String, nullable=True)
    data_source = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

