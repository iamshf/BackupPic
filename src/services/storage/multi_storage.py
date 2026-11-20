from typing import List
from src.services.storage.base_storage import BaseStorage
from src.common.exceptions import StorageError
from src.models.storage_fail_log import StorageFailLog
from src.repositories.storage_fail_log_repo import StorageFailLogRepo
import logging

logger = logging.getLogger("archive")

class MultiStorage(BaseStorage):
    """多存储聚合，支持严格模式 / 宽松模式"""
    def __init__(self, backends: List[BaseStorage], strict_mode: bool = False):
        self.backends = backends
        self.strict_mode = strict_mode

    def save(self, src_path: str, dst_key: str, session=None, file_info_id: int = None):
        """
        session、file_info_id 用于宽松模式写入失败日志
        strict=True：任意失败抛异常
        strict=False：失败打日志、入库记录，继续其他后端
        """
        for b in self.backends:
            backend_name = type(b).__name__
            try:
                logger.info(f"[MultiStorage] 开始写入后端 {backend_name}")
                b.save(src_path, dst_key)
                logger.info(f"[MultiStorage] {backend_name} 写入成功, dst_key={dst_key}")
            except Exception as e:
                err_msg = f"{backend_name} 存储失败: {str(e)}"
                logger.error(err_msg)
                if session is not None and file_info_id is not None:
                    StorageFailLogRepo.create(session, StorageFailLog(
                        file_info_id=file_info_id,
                        backend_name=backend_name,
                        dst_key=dst_key,
                        error_msg=err_msg
                    ))
                if self.strict_mode:
                    raise StorageError(err_msg) from e

    def exists(self, dst_key: str) -> bool:
        for b in self.backends:
            if not b.exists(dst_key):
                return False
        return True

    def get_full_path(self, dst_key: str) -> str:
        if self.backends:
            return self.backends[0].get_full_path(dst_key)
        return ""
