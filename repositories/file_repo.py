from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, BigInteger
from core.db import Base
from datetime import datetime

class FileRecord(Base):
    __tablename__ = "file_record"
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_filepath = Column(String(1024), nullable=False, index=True)
    file_hash = Column(String(128), nullable=False, index=True)
    filename = Column(String(256), nullable=False)
    ext_name = Column(String(32))
    mimetype = Column(String(128))
    file_size = Column(BigInteger, nullable=False)
    create_dt = Column(DateTime, nullable=False)
    target_relative_path = Column(String(1024), nullable=False)
    local_saved = Column(Integer, default=0)
    baidu_saved = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FileRecordRepo:
    @staticmethod
    def get_by_original_path(db: Session, path: str):
        return db.query(FileRecord).filter(FileRecord.original_filepath == path).first()

    @staticmethod
    def get_by_hash(db: Session, file_hash: str):
        return db.query(FileRecord).filter(FileRecord.file_hash == file_hash).first()

    @staticmethod
    def add(db: Session, record: FileRecord):
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def update(db: Session):
        db.commit()
