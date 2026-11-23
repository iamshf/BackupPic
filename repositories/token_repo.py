from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime
from core.db import Base
from datetime import datetime

class StorageToken(Base):
    __tablename__ = "storage_token"
    id = Column(Integer, primary_key=True, autoincrement=True)
    storage_type = Column(String(20), nullable=False, unique=True)
    access_token = Column(String(512))
    refresh_token = Column(String(512))
    expire_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StorageTokenRepo:
    @staticmethod
    def get_by_type(db: Session, stype: str):
        return db.query(StorageToken).filter(StorageToken.storage_type == stype).first()

    @staticmethod
    def save_or_update(db: Session, token: StorageToken):
        db.add(token)
        db.commit()
        db.refresh(token)
        return token
