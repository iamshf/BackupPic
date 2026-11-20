from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.db.base_crud import BaseCRUD
from src.models.file_info import FileInfo

class FileInfoRepo(BaseCRUD):
    model = FileInfo

    @classmethod
    def get_by_hash(cls, session: Session, filehash: str) -> Optional[FileInfo]:
        return session.scalar(select(FileInfo).where(FileInfo.filehash == filehash).limit(1))

    @classmethod
    def get_by_src_path(cls, session: Session, src_path: str) -> Optional[FileInfo]:
        return session.scalar(select(FileInfo).where(FileInfo.src_filepath == src_path).limit(1))
