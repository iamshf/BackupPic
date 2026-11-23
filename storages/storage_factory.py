from typing import List, Dict
from sqlalchemy.orm import Session
from core.settings import settings
from storages.base_storage import BaseStorage
from storages.local_storage import LocalStorage
from storages.baidu_pan_storage import BaiduPanStorage
from core.logger import logger

class MultiStorage:
    def __init__(self, backends: List[tuple[str, BaseStorage]], strict_mode: bool):
        self.backends = backends
        self.strict_mode = strict_mode

    def save(self, local_file_path: str, rel_path: str, file_record) -> Dict[str, bool]:
        result: Dict[str, bool] = {}
        for name, backend in self.backends:
            try:
                ok = backend.save(local_file_path, rel_path, file_record)
                result[name] = ok
            except Exception as e:
                logger.error(f"存储后端 [{name}] 异常: {e}")
                result[name] = False
                if self.strict_mode:
                    raise
        return result


class StorageFactory:
    @staticmethod
    def get_storage(db: Session) -> MultiStorage | BaseStorage:
        driver = settings.storage_driver.lower()
        if driver == "local":
            return LocalStorage(settings.local_target_dir)
        elif driver == "baidupcs":
            return BaiduPanStorage(
                db=db,
                client_id=settings.baidu_client_id,
                client_secret=settings.baidu_client_secret,
                chunk_size=settings.baidu_chunk_size,
                retry_times=settings.baidu_retry_times,
                refresh_threshold_hour=settings.baidu_refresh_threshold_hour
            )
        elif driver == "multi":
            instances: list[tuple[str, BaseStorage]] = []
            for bk in settings.multi_backend_list:
                if bk == "local":
                    instances.append(("local", LocalStorage(settings.local_target_dir)))
                elif bk == "baidupcs":
                    instances.append(("baidupcs", BaiduPanStorage(
                        db=db,
                        client_id=settings.baidu_client_id,
                        client_secret=settings.baidu_client_secret,
                        chunk_size=settings.baidu_chunk_size,
                        retry_times=settings.baidu_retry_times,
                        refresh_threshold_hour=settings.baidu_refresh_threshold_hour
                    )))
                else:
                    raise ValueError(f"不支持的后端: {bk}")
            return MultiStorage(instances, settings.multi_strict_mode)
        else:
            raise ValueError(f"不支持的storage driver: {driver}")
