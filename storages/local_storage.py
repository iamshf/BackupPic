from pathlib import Path
import shutil
from storages.base_storage import BaseStorage
from repositories.file_repo import FileRecord
from core.logger import logger

class LocalStorage(BaseStorage):
    def __init__(self, target_root: str):
        self.target_root = Path(target_root)

    def save(self, local_file_path: str, rel_path: str, file_record: FileRecord) -> bool:
        dst_path = self.target_root / rel_path
        if dst_path.exists():
            logger.info(f"本地已存在，跳过：{dst_path}")
            return True
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(local_file_path, dst_path)
            logger.info(f"本地备份成功 -> {dst_path}")
            return True
        except Exception as e:
            logger.error(f"本地备份失败 {local_file_path} -> {dst_path}, err:{e}")
            return False
