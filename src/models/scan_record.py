from sqlalchemy import Column, Integer
from src.db.base import Base

class ScanRecord(Base):
    __tablename__ = "scan_record"
    id = Column(Integer, primary_key=True, autoincrement=True)
    last_scan_ts = Column(Integer, nullable=False)
