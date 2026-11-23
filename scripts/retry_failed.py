# scripts/retry_failed.py
from sqlalchemy.orm import Session
from core.logger import logger
from repositories.file_repo import FileRecord
from storages.base_storage import BaseStorage
from storages.local_storage import LocalStorage
from storages.baidu_pan_storage import BaiduPanStorage
from core.settings import settings

def run_retry_failed(db: Session, target: str):
    """
    target: local / baidupcs / all
    """
    query = db.query(FileRecord)
    if target == "local":
        query = query.filter(FileRecord.local_saved == 0)
    elif target == "baidupcs":
        query = query.filter(FileRecord.baidu_saved == 0)
    elif target == "all":
        query = query.filter((FileRecord.local_saved == 0) | (FileRecord.baidu_saved == 0))
    else:
        raise ValueError("target 只能是 local / baidupcs / all")

    records = query.all()
    if not records:
        logger.info("✅ 没有待重试的失败文件")
        return

    logger.info(f"一共找到 {len(records)} 条待重试记录，target={target}")

    # 初始化后端实例
    local_storage = LocalStorage(settings.local_target_dir)
    baidu_storage = BaiduPanStorage(
        db=db,
        client_id=settings.baidu_client_id,
        client_secret=settings.baidu_client_secret,
        chunk_size=settings.baidu_chunk_size,
        retry_times=settings.baidu_retry_times,
        refresh_threshold_hour=settings.baidu_refresh_threshold_hour
    )

    for rec in records:
        fp = rec.original_filepath
        rel_path = rec.target_relative_path
        logger.info(f"==== 处理文件: {fp} ====")

        if target in ("local", "all") and rec.local_saved == 0:
            try:
                ok = local_storage.save(fp, rel_path, rec)
                if ok:
                    rec.local_saved = 1
                    logger.info(f"[local] 重试成功 {fp}")
                else:
                    logger.error(f"[local] 重试失败 {fp}")
            except Exception as e:
                logger.error(f"[local] 重试异常 {fp}, err={e}")

        if target in ("baidupcs", "all") and rec.baidu_saved == 0:
            try:
                ok = baidu_storage.save(fp, rel_path, rec)
                if ok:
                    rec.baidu_saved = 1
                    logger.info(f"[baidupcs] 重试成功 {fp}")
                else:
                    logger.error(f"[baidupcs] 重试失败 {fp}")
            except Exception as e:
                logger.error(f"[baidupcs] 重试异常 {fp}, err={e}")
        db.commit()
    logger.info("✅ 批量重试任务执行完毕")
