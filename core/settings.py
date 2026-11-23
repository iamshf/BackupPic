import configparser
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CFG_PATH = BASE_DIR / "config.ini"

cfg = configparser.ConfigParser()
cfg.read(CFG_PATH, encoding="utf-8")

class Settings:
    # db
    db_path: str = cfg.get("db", "db_path")
    # log
    log_dir: str = cfg.get("log", "log_dir")
    log_level: str = cfg.get("log", "log_level")

    # common
    source_dir: str = cfg.get("common", "source_dir")
    local_target_dir: str = cfg.get("common", "local_target_dir")
    scan_recursive: bool = cfg.getboolean("common", "scan_recursive")

    # storage
    storage_driver: str = cfg.get("storage", "driver")
    multi_backend_list: list[str] = [x.strip().lower() for x in cfg.get("storage", "multi_backend_list").split(",")]
    multi_strict_mode: bool = cfg.getboolean("storage", "multi_strict_mode")

    # baidu pan
    baidu_client_id: str = cfg.get("baidu_pan", "client_id")
    baidu_client_secret: str = cfg.get("baidu_pan", "client_secret")
    baidu_retry_times: int = cfg.getint("baidu_pan", "upload_retry_times")
    baidu_chunk_size: int = cfg.getint("baidu_pan", "chunk_size")
    baidu_refresh_threshold_hour: int = cfg.getint("baidu_pan", "refresh_threshold_hour")
    baidu_remote_root: str = cfg.get("baidu_pan", "remote_root", fallback="/")

settings = Settings()
