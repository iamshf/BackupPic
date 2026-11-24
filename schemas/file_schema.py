from pydantic import BaseModel
from datetime import datetime

class FileInfoSchema(BaseModel):
    original_filepath: str
    file_hash: str
    file_md5: str
    filename: str
    ext_name: str
    mimetype: str
    file_size: int
    create_dt: datetime
    target_relative_path: str
