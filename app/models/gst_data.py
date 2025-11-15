from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid


class GSTData(Base):
    __tablename__ = "gst_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    gstin = Column(String, unique=True, nullable=False, index=True)
    legal_name = Column(String, nullable=True, index=True)
    trade_name = Column(String, nullable=True)
    business_constitution = Column(String, nullable=True)
    aggregate_turn_over = Column(String, nullable=True)
    authorized_signatory = Column(JSON, nullable=True)  # Array of names
    business_details = Column(JSON, nullable=True)  # {bzsdtls: [{saccd, sdes}]}
    business_nature = Column(JSON, nullable=True)  # Array
    can_flag = Column(String, nullable=True)
    central_jurisdiction = Column(Text, nullable=True)
    compliance_rating = Column(String, nullable=True)
    current_registration_status = Column(String, nullable=True)
    filing_status = Column(JSON, nullable=True)  # Nested array structure
    is_field_visit_conducted = Column(String, nullable=True)
    mandate_e_invoice = Column(String, nullable=True)
    other_business_address = Column(JSON, nullable=True)
    primary_business_address = Column(JSON, nullable=True)  # {business_nature, detailed_address, registered_address, last_updated_date}
    register_cancellation_date = Column(String, nullable=True)
    register_date = Column(String, nullable=True)
    state_jurisdiction = Column(Text, nullable=True)
    tax_payer_type = Column(String, nullable=True)
    gross_total_income = Column(String, nullable=True)
    gross_total_income_financial_year = Column(String, nullable=True)
    data_source = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

