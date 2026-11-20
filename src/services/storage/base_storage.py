from abc import ABC, abstractmethod
from src.common.exceptions import StorageError

class BaseStorage(ABC):
    """统一存储抽象，本地、OSS、COS、S3 都实现这个接口"""
    @abstractmethod
    def save(self, src_path: str, dst_key: str):
        """
        src_path: 本地源文件
        dst_key: 目标路径key，本地是相对路径，云是object key
        """
        ...

    @abstractmethod
    def exists(self, dst_key: str) -> bool:
        ...

    @abstractmethod
    def get_full_path(self, dst_key: str) -> str:
        """用于入库记录，本地返回绝对路径，云返回url"""
        ...
