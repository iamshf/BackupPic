import os
import time
import requests
import logging
from typing import Optional
from src.services.storage.base_storage import BaseStorage
from src.common.exceptions import StorageError, retry

TOKEN_URL = "https://openapi.baidu.com/oauth/2.0/token"
UPLOAD_PRECREATE_URL = "https://pan.baidu.com/rest/2.0/xpan/file?method=precreate"
UPLOAD_UPLOAD_URL = "https://d.pcs.baidu.com/rest/2.0/pcs/file?method=upload"
UPLOAD_COMMIT_URL = "https://pan.baidu.com/rest/2.0/xpan/file?method=create"
FILE_META_URL = "https://pan.baidu.com/rest/2.0/xpan/file?method=meta"

logger = logging.getLogger("archive")

class BaiduPcsStorage(BaseStorage):
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        refresh_token: str,
        pcs_root_dir: str,
        chunk_size: int = 4 * 1024 * 1024
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.refresh_token = refresh_token
        self.pcs_root_dir = pcs_root_dir.rstrip("/")
        self.chunk_size = chunk_size
        self.access_token: Optional[str] = None
        self.token_expire_ts: int = 0
        self._refresh_access_token()

    @retry(times=3, delay=2)
    def _refresh_access_token(self):
        resp = requests.get(
            TOKEN_URL,
            params={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.app_id,
                "client_secret": self.app_secret
            },
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        expires_in = data["expires_in"]
        self.token_expire_ts = int(time.time()) + expires_in - 60

    def _get_valid_token(self) -> str:
        if time.time() >= self.token_expire_ts:
            self._refresh_access_token()
        return self.access_token

    def _get_pcs_full_path(self, dst_key: str) -> str:
        return f"{self.pcs_root_dir}/{dst_key}"

    @retry(times=3, delay=2)
    def exists(self, dst_key: str) -> bool:
        remote_path = self._get_pcs_full_path(dst_key)
        token = self._get_valid_token()
        resp = requests.get(
            FILE_META_URL,
            params={
                "access_token": token,
                "path": remote_path
            },
            timeout=30
        )
        if resp.status_code == 200:
            return True
        return False

    def get_full_path(self, dst_key: str) -> str:
        return self._get_pcs_full_path(dst_key)

    @retry(times=3, delay=2)
    def save(self, src_path: str, dst_key: str):
        remote_path = self._get_pcs_full_path(dst_key)
        token = self._get_valid_token()
        file_size = os.path.getsize(src_path)
        if file_size <= 0:
            raise StorageError("源文件大小为0，跳过上传")

        total_chunk = (file_size + self.chunk_size - 1) // self.chunk_size
        logger.info(f"[百度PCS] 开始上传 {src_path} -> {remote_path}，总大小 {file_size/1024/1024:.2f} MB，分片数：{total_chunk}")

        pre_resp = requests.post(
            UPLOAD_PRECREATE_URL,
            params={"access_token": token},
            json={
                "path": remote_path,
                "size": file_size,
                "isdir": 0,
                "autoinit": 1
            },
            timeout=30
        )
        pre_resp.raise_for_status()
        pre_data = pre_resp.json()
        upload_id = pre_data["uploadid"]

        with open(src_path, "rb") as f:
            offset = 0
            seq = 0
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                @retry(times=3, delay=2)
                def upload_one_part():
                    r = requests.post(
                        UPLOAD_UPLOAD_URL,
                        params={
                            "access_token": token,
                            "path": remote_path,
                            "uploadid": upload_id,
                            "partseq": seq,
                            "offset": offset
                        },
                        files={"file": chunk},
                        timeout=120
                    )
                    r.raise_for_status()
                    return r
                upload_one_part()
                offset += len(chunk)
                seq += 1
                logger.info(f"[百度PCS] 分片进度 {seq}/{total_chunk}，已上传 {offset/1024/1024:.2f} MB")

        commit_resp = requests.post(
            UPLOAD_COMMIT_URL,
            params={"access_token": token},
            json={
                "path": remote_path,
                "uploadid": upload_id,
                "size": file_size,
                "isdir": 0
            },
            timeout=60
        )
        commit_resp.raise_for_status()
        logger.info(f"[百度PCS] 上传完成：{remote_path}")
