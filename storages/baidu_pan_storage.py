import requests
import time
import datetime
from sqlalchemy.orm import Session
from pathlib import Path
from core import settings
from storages.base_storage import BaseStorage
from repositories.token_repo import StorageTokenRepo, StorageToken
from repositories.file_repo import FileRecord
from core.logger import logger
from exceptions import TokenRefreshError, StorageError
from functools import wraps

def retry(max_retry):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retry):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"百度网盘接口异常，重试{i+1}/{max_retry} err:{e}")
                    time.sleep(2)
            logger.error(f"百度网盘重试全部失败: {func.__name__}")
            return None
        return wrapper
    return decorator

class BaiduPanStorage(BaseStorage):
    def __init__(self, db: Session, client_id: str, client_secret: str, chunk_size: int, retry_times: int, refresh_threshold_hour: int):
        self.db = db
        self.client_id = client_id
        self.client_secret = client_secret
        self.chunk_size = chunk_size
        self.retry_times = retry_times
        self.refresh_threshold = datetime.timedelta(hours=refresh_threshold_hour)

    def _authorize_by_code(self, code: str):
        url = "https://openapi.baidu.com/oauth/2.0/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": "oob"
        }
        resp = requests.post(url, data=data, timeout=15)
        ret = resp.json()
        if "error" in ret:
            logger.error(f"授权换取token失败：{ret}")
            return None
        now = datetime.datetime.utcnow()
        expire_at = now + datetime.timedelta(seconds=ret["expires_in"])
        token_row = StorageTokenRepo.get_by_type(self.db, "baidupcs")
        if token_row:
            token_row.access_token = ret["access_token"]
            token_row.refresh_token = ret["refresh_token"]
            token_row.expire_at = expire_at
        else:
            token_row = StorageToken(
                storage_type="baidupcs",
                access_token=ret["access_token"],
                refresh_token=ret["refresh_token"],
                expire_at=expire_at
            )
        StorageTokenRepo.save_or_update(self.db, token_row)
        logger.info("✅ 百度网盘token已保存")
        return ret["access_token"]

    def _refresh_token(self, old_refresh_token: str):
        url = "https://openapi.baidu.com/oauth/2.0/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": old_refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        resp = requests.post(url, data=data, timeout=15)
        ret = resp.json()
        if "error" in ret:
            logger.error(f"刷新token失败：{ret}")
            raise TokenRefreshError(str(ret))
        now = datetime.datetime.utcnow()
        expire_at = now + datetime.timedelta(seconds=ret["expires_in"])
        token_row = StorageTokenRepo.get_by_type(self.db, "baidupcs")
        token_row.access_token = ret["access_token"]
        token_row.refresh_token = ret["refresh_token"]
        token_row.expire_at = expire_at
        StorageTokenRepo.save_or_update(self.db, token_row)
        logger.info("✅ 百度网盘token自动刷新成功")
        return ret["access_token"]

    def get_valid_access_token(self):
        token_row = StorageTokenRepo.get_by_type(self.db, "baidupcs")
        now = datetime.datetime.utcnow()
        if not token_row:
            auth_url = "https://openapi.baidu.com/oauth/2.0/authorize?response_type=code&client_id=" + self.client_id + "&redirect_uri=oob&scope=basic,netdisk"
            print("\n===== 未检测到百度网盘授权token =====")
            print(f"打开链接授权：{auth_url}")
            code = input("粘贴授权code：").strip()
            return self._authorize_by_code(code)
        if token_row.expire_at and (token_row.expire_at - now) < self.refresh_threshold:
            logger.info("access_token即将过期，执行刷新")
            return self._refresh_token(token_row.refresh_token)
        return token_row.access_token

    @retry(max_retry=3)
    def _remote_file_exists(self, access_token: str, remote_path: str) -> bool:
        url = "https://pan.baidu.com/rest/2.0/xpan/file"
        params = {
            "method": "list",
            "access_token": access_token,
            "path": str(Path(remote_path).parent),
            "recursion": 0
        }
        r = requests.get(url, params=params, timeout=20)
        j = r.json()
        if j.get("errno") != 0:
            raise StorageError(f"list接口查询失败 {j}")
        file_name = Path(remote_path).name
        for item in j.get("list", []):
            if item["isdir"] == 0 and item["server_filename"] == file_name:
                return True
        return False

    @retry(max_retry=3)
    def _precreate(self, access_token: str, remote_path: str, file_size: int):
        url = "https://pan.baidu.com/rest/2.0/xpan/file"
        params = {"method": "precreate", "access_token": access_token}
        payload = {
            "path": remote_path,
            "size": file_size,
            "isdir": 0,
            "autoinit": 1
        }
        r = requests.post(url, params=params, json=payload, timeout=20)
        j = r.json()
        if j.get("errno") != 0:
            raise StorageError(f"precreate err {j}")
        return j["uploadid"]

    @retry(max_retry=3)
    def _upload_chunk(self, access_token: str, uploadid: str, remote_path: str, chunk_data, seq: int):
        url = "https://pan.baidu.com/rest/2.0/xpan/file?method=upload"
        params = {
            "access_token": access_token,
            "uploadid": uploadid,
            "path": remote_path,
            "partseq": seq
        }
        files = {"file": chunk_data}
        r = requests.post(url, params=params, files=files, timeout=60)
        j = r.json()
        if j.get("errno") != 0:
            raise StorageError(f"分片上传 err {j}")
        return True

    @retry(max_retry=3)
    def _commit(self, access_token: str, uploadid: str, remote_path: str, file_size: int):
        url = "https://pan.baidu.com/rest/2.0/xpan/file"
        params = {"method": "create", "access_token": access_token}
        payload = {
            "path": remote_path,
            "uploadid": uploadid,
            "size": file_size,
            "isdir": 0
        }
        r = requests.post(url, params=params, json=payload, timeout=20)
        j = r.json()
        if j.get("errno") != 0:
            raise StorageError(f"commit err {j}")
        return True

    def save(self, local_file_path: str, rel_path: str, file_record: FileRecord) -> bool:
        access_token = self.get_valid_access_token()
        if not access_token:
            return False
        
        remote_root = settings.baidu_remote_root.rstrip("/")
        remote_path = f"{remote_root}/{rel_path}"
        remote_dir = str(Path(remote_path).parent)

        self._mkdir(access_token, remote_dir)

        exists = self._remote_file_exists(access_token, remote_path)
        if exists:
            logger.info(f"百度网盘已存在，跳过上传：{remote_path}")
            return True
        local_fp = Path(local_file_path)
        file_size = local_fp.stat().st_size
        logger.info(f"开始百度网盘上传：{remote_path} size={file_size}")
        uploadid = self._precreate(access_token, remote_path, file_size)
        if not uploadid:
            return False
        with open(local_fp, "rb") as f:
            seq = 0
            while chunk := f.read(self.chunk_size):
                access_token = self.get_valid_access_token()
                if not access_token:
                    return False
                self._upload_chunk(access_token, uploadid, remote_path, chunk, seq)
                logger.info(f"百度网盘分片 {seq} 上传完成")
                seq += 1
        access_token = self.get_valid_access_token()
        ok = self._commit(access_token, uploadid, remote_path, file_size)
        if ok:
            logger.info(f"百度网盘上传成功 {remote_path}")
            return True
        return False

    
    @retry(max_retry=3)
    def _mkdir(self, access_token: str, remote_dir: str):
        url = "https://pan.baidu.com/rest/2.0/xpan/file"
        params = {"method": "create", "access_token": access_token}
        payload = {
            "path": remote_dir,
            "isdir": 1
        }
        r = requests.post(url, params=params, json=payload, timeout=20)
        j = r.json()
        # 目录已存在（errno=3106）不算错误
        if j.get("errno") not in (0, 3106):
            raise StorageError(f"创建目录失败 {remote_dir} , resp:{j}")
        return True

