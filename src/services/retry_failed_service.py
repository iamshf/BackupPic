import logging
from sqlalchemy.orm import Session
from src.repositories.storage_fail_log_repo import StorageFailLogRepo
from src.repositories.file_info_repo import FileInfoRepo
from src.services.storage.base_storage import BaseStorage

logger = logging.getLogger("archive")

class RetryFailedService:
    def __init__(self, storage: BaseStorage):
        self.storage = storage

    def run_retry(self, session: Session):
        fail_list = StorageFailLogRepo.list_unfixed(session)
        if not fail_list:
            logger.info("没有待重试的失败记录")
            return
        logger.info(f"待重试记录数量：{len(fail_list)}")
        for log_item in fail_list:
            file_info = FileInfoRepo.get_by_id(session, log_item.file_info_id)
            if not file_info:
                logger.warning(f"找不到file记录 id={log_item.file_info_id}，跳过")
                log_item.fixed = 1
                continue
            try:
                self.storage.save(file_info.src_filepath, log_item.dst_key)
                log_item.fixed = 1
                logger.info(f"重试成功 id={log_item.id}")
            except Exception as e:
                logger.error(f"重试失败 id={log_item.id}, err: {e}")
        session.commit()
        logger.info("重试任务执行完毕")
