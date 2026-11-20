from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.db.base_crud import BaseCRUD
from src.models.storage_fail_log import StorageFailLog

class StorageFailLogRepo(BaseCRUD):
    model = StorageFailLog

    @classmethod
    def list_unfixed(cls, session: Session) -> List[StorageFailLog]:
        return session.scalars(select(StorageFailLog).where(StorageFailLog.fixed == 0)).all()
