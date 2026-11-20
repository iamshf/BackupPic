import configparser
import os
from typing import Dict

def load_config(ini_path: str = "config.ini") -> Dict:
    cfg = configparser.ConfigParser()
    cfg.read(ini_path, encoding="utf-8-sig")

    conf = {
        "source_dir": cfg.get("scan", "source_dir").strip(),
        "target_root": cfg.get("scan", "target_root").strip(),
        "batch_size": cfg.getint("scan", "batch_size"),
        "db_url": cfg.get("db", "db_url").strip(),
        "log_file": cfg.get("log", "log_file").strip(),
        "log_level": cfg.get("log", "log_level").strip(),
        "storage_driver": cfg.get("storage", "driver").strip(),
        "multi_backend_list": cfg.get("storage", "multi_backend_list", fallback=""),
        "multi_strict_mode": cfg.getboolean("storage", "multi_strict_mode", fallback=False),
        "pcs_app_id": cfg.get("storage", "pcs_app_id", fallback=""),
        "pcs_app_secret": cfg.get("storage", "pcs_app_secret", fallback=""),
        "pcs_refresh_token": cfg.get("storage", "pcs_refresh_token", fallback=""),
        "pcs_root_dir": cfg.get("storage", "pcs_root_dir", fallback="/archive"),
    }
    log_parent = os.path.dirname(conf["log_file"])
    if log_parent:
        os.makedirs(log_parent, exist_ok=True)
    return conf
