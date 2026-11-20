import logging
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from src.models.file_info import FileInfo
from src.repositories.file_info_repo import FileInfoRepo
from src.repositories.scan_repo import ScanRecordRepo
from src.models.scan_record import ScanRecord
from src.services.storage.base_storage import BaseStorage
from src.services.storage.multi_storage import MultiStorage
from src.utils.file_tool import (
    get_file_mtime_ts, calc_sha256, get_file_mime,
    get_file_ctime_ts, make_safe_dst_name, ts_to_path_key
)
from src.common.exceptions import ArchiveError

logger = logging.getLogger("archive")

class ArchiveService:
    def __init__(self, storage: BaseStorage, batch_size: int):
        self.storage = storage
        self.batch_size = batch_size

    def run_scan(self, session: Session, source_dir: str):
        buffer: List[FileInfo] = []
        total_files = 0
        skip_by_src = 0
        skip_by_hash = 0
        uploaded = 0
        scan_start_ts = int(datetime.now().timestamp())

        last_rec = ScanRecordRepo.get_last(session)
        last_scan_ts = last_rec.last_scan_ts if last_rec else 0
        logger.info(f"上次扫描时间戳：{last_scan_ts}，本次扫描开始")

        for root, _, files in os.walk(source_dir):
            for fname in files:
                src_full = os.path.abspath(os.path.join(root, fname))
                total_files += 1
                try:
                    mtime = get_file_mtime_ts(src_full)
                    if mtime < last_scan_ts:
                        continue
                except Exception as e:
                    logger.warning(f"读取文件mtime失败 {src_full}: {e}")
                    continue

                logger.info(f"处理文件：{src_full}")
                exist_src = FileInfoRepo.get_by_src_path(session, src_full)
                if exist_src:
                    skip_by_src += 1
                    continue

                try:
                    file_hash = calc_sha256(src_full)
                    fsize = os.path.getsize(src_full)
                    mime = get_file_mime(src_full)
                    ctime = get_file_ctime_ts(src_full)
                except Exception as e:
                    logger.error(f"读取文件信息失败 {src_full}: {e}")
                    continue

                exist_hash = FileInfoRepo.get_by_hash(session, file_hash)
                if exist_hash:
                    skip_by_hash += 1
                    continue

                dst_filename = make_safe_dst_name(fname, file_hash)
                dst_key = f"{ts_to_path_key(ctime)}/{dst_filename}"

                if isinstance(self.storage, MultiStorage):
                    new_file = FileInfo(
                        filename=fname,
                        filehash=file_hash,
                        filesize=fsize,
                        mimetype=mime,
                        gmt_createtime=ctime,
                        src_filepath=src_full,
                        dst_filename=dst_filename
                    )
                    FileInfoRepo.create(session, new_file)
                    session.flush()
                    self.storage.save(src_full, dst_key, session=session, file_info_id=new_file.id)
                else:
                    self.storage.save(src_full, dst_key)
                    new_file = FileInfo(
                        filename=fname,
                        filehash=file_hash,
                        filesize=fsize,
                        mimetype=mime,
                        gmt_createtime=ctime,
                        src_filepath=src_full,
                        dst_filename=dst_filename
                    )
                buffer.append(new_file)
                uploaded += 1

                if len(buffer) >= self.batch_size:
                    self._batch_insert(session, buffer)
                    buffer.clear()

        if buffer:
            self._batch_insert(session, buffer)

        ScanRecordRepo.create(session, ScanRecord(last_scan_ts=scan_start_ts))
        session.commit()

        logger.info("=====扫描归档汇总=====")
        logger.info(f"扫描总文件数：{total_files}")
        logger.info(f"按源路径跳过：{skip_by_src}")
        logger.info(f"按hash去重跳过：{skip_by_hash}")
        logger.info(f"本次新增归档：{uploaded}")

    def _batch_insert(self, session: Session, items: List[FileInfo]):
        try:
            FileInfoRepo.batch_create(session, items)
            session.commit()
            logger.info(f"批量入库 {len(items)} 条成功")
        except Exception as e:
            session.rollback()
            logger.error(f"批量提交失败，降级逐条插入：{e}")
            for it in items:
                try:
                    FileInfoRepo.create(session, it)
                    session.commit()
                except Exception as ee:
                    session.rollback()
                    logger.error(f"单条入库失败 src={it.src_filepath}, err={ee}")
