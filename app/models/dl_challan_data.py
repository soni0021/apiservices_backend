from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.sql import func
from app.database import Base
import uuid


class DLChallanData(Base):
    __tablename__ = "dl_challan_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dl_no = Column(String, nullable=False, index=True)
    reg_no = Column(String, nullable=True, index=True)
    state = Column(String, nullable=True)
    rto = Column(String, nullable=True)
    reg_date = Column(String, nullable=True)
    status = Column(String, nullable=True)
    owner_name = Column(String, nullable=True, index=True)
    father_name = Column(String, nullable=True)
    permanent_address = Column(Text, nullable=True)
    present_address = Column(Text, nullable=True)
    mobile_no = Column(String, nullable=True)
    owner_sr_no = Column(Integer, nullable=True)
    vehicle_class = Column(String, nullable=True)
    maker = Column(String, nullable=True)
    maker_model = Column(String, nullable=True)
    fuel_type = Column(String, nullable=True)
    data_source = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

