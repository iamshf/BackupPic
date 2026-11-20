from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from src.db.base_crud import BaseCRUD
from src.models.scan_record import ScanRecord

class ScanRecordRepo(BaseCRUD):
    model = ScanRecord

    @classmethod
    def get_last(cls, session: Session) -> Optional[ScanRecord]:
        return session.scalar(select(ScanRecord).order_by(desc(ScanRecord.id)).limit(1))
