import os
import shutil
from src.services.storage.base_storage import BaseStorage
from src.common.exceptions import StorageError
from src.common.exceptions import retry

class LocalStorage(BaseStorage):
    def __init__(self, root: str):
        self.root = root

    @retry(times=2, delay=1)
    def save(self, src_path: str, dst_key: str):
        full_dst = os.path.join(self.root, dst_key)
        dirname = os.path.dirname(full_dst)
        os.makedirs(dirname, exist_ok=True)
        try:
            shutil.copy2(src_path, full_dst)
        except Exception as e:
            raise StorageError(f"本地复制失败 {src_path} -> {full_dst}") from e

    def exists(self, dst_key: str) -> bool:
        full_dst = os.path.join(self.root, dst_key)
        return os.path.exists(full_dst)

    def get_full_path(self, dst_key: str) -> str:
        return os.path.abspath(os.path.join(self.root, dst_key))
