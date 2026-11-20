from sqlalchemy import Column, Integer, String, Text
from src.db.base import Base

class FileInfo(Base):
    __tablename__ = "file_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(300), nullable=False)
    filehash = Column(String(64), nullable=False, index=True)
    filesize = Column(Integer, nullable=False)
    mimetype = Column(String(50), nullable=False)
    gmt_createtime = Column(Integer, nullable=False)
    src_filepath = Column(Text, nullable=False, unique=True)
    dst_filename = Column(Text, nullable=False)
