from abc import ABC, abstractmethod
from typing import Dict

class BaseStorage(ABC):
    @abstractmethod
    def save(self, local_file_path: str, rel_path: str, file_record) -> bool:
        pass
