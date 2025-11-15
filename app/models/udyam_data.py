from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.database import Base
import uuid


class UdyamData(Base):
    __tablename__ = "udyam_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String, nullable=False, index=True)
    udyam_number = Column(String, nullable=True, index=True)
    enterprise_name = Column(String, nullable=True, index=True)
    data_source = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

