import logging
from sqlalchemy.orm import Session
from src.repositories.file_info_repo import FileInfoRepo
from src.services.storage.base_storage import BaseStorage
from src.utils.file_tool import ts_to_path_key

logger = logging.getLogger("archive")

class CheckService:
    def __init__(self, storage: BaseStorage):
        self.storage = storage

    def run_check(self, session: Session):
        all_records = FileInfoRepo.list_all(session)
        missing = 0
        for rec in all_records:
            rel_key = ts_to_path_key(rec.gmt_createtime)
            dst_key = f"{rel_key}/{rec.dst_filename}"
            if not self.storage.exists(dst_key):
                logger.warning(f"缺失归档记录 id={rec.id}, src={rec.src_filepath}")
                missing += 1
        logger.info(f"校验完成，总记录 {len(all_records)}，缺失 {missing}")
