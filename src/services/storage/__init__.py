from src.services.storage.base_storage import BaseStorage
from src.services.storage.local_storage import LocalStorage
from src.services.storage.baidupcs_storage import BaiduPcsStorage
from src.services.storage.multi_storage import MultiStorage

def get_storage_driver(driver_name: str, target_root: str, cfg: dict = None) -> BaseStorage:
    if driver_name == "local":
        return LocalStorage(target_root)
    elif driver_name == "baidupcs":
        if cfg is None:
            raise RuntimeError("baidupcs驱动需要传入完整配置字典")
        return BaiduPcsStorage(
            app_id=cfg["pcs_app_id"],
            app_secret=cfg["pcs_app_secret"],
            refresh_token=cfg["pcs_refresh_token"],
            pcs_root_dir=cfg["pcs_root_dir"]
        )
    elif driver_name == "multi":
        if cfg is None:
            raise RuntimeError("multi驱动需要传入完整配置字典")
        backend_names = [x.strip() for x in cfg["multi_backend_list"].split(",") if x.strip()]
        backends = []
        for b_name in backend_names:
            if b_name == "local":
                backends.append(LocalStorage(target_root))
            elif b_name == "baidupcs":
                backends.append(BaiduPcsStorage(
                    app_id=cfg["pcs_app_id"],
                    app_secret=cfg["pcs_app_secret"],
                    refresh_token=cfg["pcs_refresh_token"],
                    pcs_root_dir=cfg["pcs_root_dir"]
                ))
            else:
                raise RuntimeError(f"multi不支持的后端：{b_name}")
        strict = cfg.get("multi_strict_mode", False)
        return MultiStorage(backends, strict_mode=strict)
    raise RuntimeError(f"不支持的存储驱动：{driver_name}")
