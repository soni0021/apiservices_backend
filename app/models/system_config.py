from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class SystemConfig(Base):
    __tablename__ = "system_configs"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

