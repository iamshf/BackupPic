import os
from pathlib import Path
from sqlalchemy.orm import Session
from core.logger import logger
from core.settings import settings
from repositories.file_repo import FileRecordRepo, FileRecord
from storages.storage_factory import StorageFactory, MultiStorage
from utils import calc_sha256, get_file_create_time, get_file_size, get_ext_name, guess_mimetype

class BackupService:
    def __init__(self, db: Session):
        self.db = db
        self.storage = StorageFactory.get_storage(db)

    def scan_and_backup(self):
        source_dir = Path(settings.source_dir)
        recursive = settings.scan_recursive
        walker = os.walk(source_dir)
        for root, dirs, files in walker:
            if not recursive:
                dirs.clear()
            for fn in files:
                full_path = str(Path(root) / fn)
                exist_rec = FileRecordRepo.get_by_original_path(self.db, full_path)
                file_hash = calc_sha256(full_path)
                file_create_dt = get_file_create_time(full_path)
                file_size = get_file_size(full_path)
                ext_name = get_ext_name(full_path)
                mimetype = guess_mimetype(full_path)
                rel_path = f"{file_create_dt.year}/{file_create_dt.month:02d}/{file_create_dt.day:02d}/{fn}"

                if exist_rec:
                    logger.info(f"数据库记录已存在，跳过源文件：{full_path}")
                    record = exist_rec
                else:
                    hash_exist = FileRecordRepo.get_by_hash(self.db, file_hash)
                    if hash_exist:
                        logger.info(f"文件hash重复，跳过：{full_path}")
                        continue
                    record = FileRecord(
                        original_filepath=full_path,
                        file_hash=file_hash,
                        filename=fn,
                        ext_name=ext_name,
                        mimetype=mimetype,
                        file_size=file_size,
                        create_dt=file_create_dt,
                        target_relative_path=rel_path,
                        local_saved=0,
                        baidu_saved=0
                    )
                    FileRecordRepo.add(self.db, record)

                # 区分multi模式和单后端
                if isinstance(self.storage, MultiStorage):
                    res_dict = self.storage.save(full_path, rel_path, record)
                    if "local" in res_dict:
                        record.local_saved = 1 if res_dict["local"] else 0
                    if "baidupcs" in res_dict:
                        record.baidu_saved = 1 if res_dict["baidupcs"] else 0
                else:
                    ok = self.storage.save(full_path, rel_path, record)
                    if isinstance(self.storage, LocalStorage):
                        record.local_saved = 1 if ok else 0
                    elif isinstance(self.storage, BaiduPanStorage):
                        record.baidu_saved = 1 if ok else 0
                FileRecordRepo.update(self.db)
        logger.info("✅ 本轮扫描备份全部完成")
