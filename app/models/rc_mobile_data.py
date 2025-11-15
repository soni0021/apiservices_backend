from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.database import Base
import uuid


class RCMobileData(Base):
    __tablename__ = "rc_mobile_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    reg_no = Column(String, unique=True, nullable=False, index=True)
    mobile_no = Column(String, nullable=True, index=True)
    data_source = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

