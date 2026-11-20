from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from src.db.base import Base

class StorageFailLog(Base):
    __tablename__ = "storage_fail_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_info_id = Column(Integer, nullable=False)
    backend_name = Column(String(100), nullable=False)
    dst_key = Column(Text, nullable=False)
    error_msg = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    fixed = Column(Integer, default=0) # 0未修复，1已修复
