import requests
import time
import datetime
import json
import hashlib
from urllib.parse import quote
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
    PCS_CHUNK_SIZE = 4 * 1024 * 1024
    UA = "pan.baidu.com/1.0"
    HEADERS = {"User-Agent": UA}
    DEBUG = True

    def __init__(self, db: Session, client_id: str, client_secret: str, chunk_size: int, retry_times: int, refresh_threshold_hour: int):
        self.db = db
        self.client_id = client_id
        self.client_secret = client_secret
        self.chunk_size = chunk_size
        self.retry_times = retry_times
        self.refresh_threshold = datetime.timedelta(hours=refresh_threshold_hour)
        self.remote_root = settings.baidu_remote_root.rstrip("/")

    @staticmethod
    def safe_json(resp: requests.Response):
        try:
            text = resp.text
            if BaiduPanStorage.DEBUG:
                logger.debug(f"[RESP RAW] status={resp.status_code}, raw={repr(text[:800])}")
            if not text.strip():
                raise RuntimeError("百度接口返回空响应")
            return resp.json()
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON解析失败，原始返回：{repr(resp.text[:800])}") from e

    @staticmethod
    def clean_remote_path(raw_path: str) -> str:
        p = raw_path.replace("\\", "/")
        while "//" in p:
            p = p.replace("//", "/")
        return p

    @staticmethod
    def split_remote_path(remote_path: str):
        p = BaiduPanStorage.clean_remote_path(remote_path)
        parts = [x for x in p.split("/") if x.strip()]
        if len(parts) == 0:
            return "/", ""
        if len(parts) == 1:
            return "/", parts[0]
        parent = "/" + "/".join(parts[:-1])
        name = parts[-1]
        return parent, name

    @staticmethod
    def calc_chunk_md5(data: bytes) -> str:
        return hashlib.md5(data).hexdigest()

    @staticmethod
    def get_file_block_list(file_path: str):
        fp = Path(file_path)
        block_list = []
        chunks = []
        with open(fp, "rb") as f:
            while True:
                chunk = f.read(BaiduPanStorage.PCS_CHUNK_SIZE)
                if not chunk:
                    break
                md5 = BaiduPanStorage.calc_chunk_md5(chunk)
                block_list.append(md5)
                chunks.append(chunk)
        return block_list, chunks

    @staticmethod
    def _encode_remote_path(remote_path: str) -> str:
        remote_path = remote_path.replace("\\", "/").strip()
        if remote_path == "/":
            return "/"
        segs = [s for s in remote_path.split("/") if s.strip()]
        return "/" + "/".join([quote(s, encoding="utf-8") for s in segs])

    @retry(max_retry=3)
    def _mkdir(self, access_token: str, remote_dir_raw: str):
        remote_dir_raw = self.clean_remote_path(remote_dir_raw)
        if remote_dir_raw == "/":
            return True
        segments = [s for s in remote_dir_raw.split("/") if s.strip()]
        current_raw = ""
        for seg in segments:
            current_raw = f"{current_raw}/{seg}"
            current_raw = self.clean_remote_path(current_raw)
            url = "https://pan.baidu.com/rest/2.0/xpan/file"
            params = {"method": "create", "access_token": access_token}
            data = {
                "path": current_raw,
                "isdir": 1,
                "rtype": 0
            }
            if self.DEBUG:
                logger.debug(f"[mkdir DEBUG] url={url}, params={params}, data={data}")
            r = requests.post(url, params=params, data=data, headers=self.HEADERS, timeout=20)
            j = self.safe_json(r)
            logger.debug(f"[mkdir] path={current_raw}, resp={j}")
            if j.get("errno") not in (0, 3106, -8):
                raise StorageError(f"创建目录失败 {current_raw}, resp={j}")
        return True

    def _authorize_by_code(self, code: str):
        url = "https://openapi.baidu.com/oauth/2.0/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": "oob"
        }
        if self.DEBUG:
            logger.debug(f"[token DEBUG] url={url}, data={data}")
        resp = requests.post(url, data=data, headers=self.HEADERS, timeout=15)
        ret = self.safe_json(resp)
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
        if self.DEBUG:
            logger.debug(f"[refresh DEBUG] url={url}, data={data}")
        resp = requests.post(url, data=data, headers=self.HEADERS, timeout=15)
        ret = self.safe_json(resp)
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
        parent_raw, file_name = self.split_remote_path(remote_path)
        parent_encoded = self._encode_remote_path(parent_raw)
        url = "https://pan.baidu.com/rest/2.0/xpan/file"
        params = {
            "method": "list",
            "access_token": access_token,
            "path": parent_encoded,
            "recursion": 0
        }
        if self.DEBUG:
            logger.debug(f"[list DEBUG] url={url}, params={params}")
        r = requests.get(url, params=params, headers=self.HEADERS, timeout=20)
        j = self.safe_json(r)
        if j.get("errno") != 0:
            raise StorageError(f"list接口查询失败 {j}")
        for item in j.get("list", []):
            if item["isdir"] == 0 and item["server_filename"] == file_name:
                return True
        return False

    @retry(max_retry=3)
    def _get_remote_file_md5(self, access_token: str, remote_path: str) -> str | None:
        parent_raw, file_name = self.split_remote_path(remote_path)
        parent_encoded = self._encode_remote_path(parent_raw)
        url = "https://pan.baidu.com/rest/2.0/xpan/file"
        params = {
            "method": "list",
            "access_token": access_token,
            "path": parent_encoded,
            "recursion": 0
        }
        if self.DEBUG:
            logger.debug(f"[list DEBUG] url={url}, params={params}")
        r = requests.get(url, params=params, headers=self.HEADERS, timeout=20)
        j = self.safe_json(r)
        if j.get("errno") != 0:
            raise StorageError(f"list接口查询失败 {j}")
        for item in j.get("list", []):
            if item["isdir"] == 0 and item["server_filename"] == file_name:
                # 百度pcs里的md5字段名是 md5
                return item.get("md5")
        return None


    @retry(max_retry=3)
    def _precreate(self, access_token: str, remote_path: str, file_size: int, block_list: list):
        url = "https://pan.baidu.com/rest/2.0/xpan/file"
        params = {"method": "precreate", "access_token": access_token}
        data = {
            "path": remote_path,
            "size": file_size,
            "isdir": 0,
            "autoinit": 1,
            "rtype": 3,
            "block_list": json.dumps(block_list)
        }
        if self.DEBUG:
            logger.debug(f"[precreate DEBUG] url={url}, params={params}, data={data}")
        r = requests.post(url, params=params, data=data, headers=self.HEADERS, timeout=20)
        j = self.safe_json(r)

        if j.get("errno") == -8:
            logger.info(f"precreate返回文件已存在 {remote_path}")
            # 这里可以再次调用 _get_remote_file_md5 二次校验
            remote_md5 = self._get_remote_file_md5(access_token, remote_path)
            return None

        if j.get("errno") != 0:
            raise StorageError(f"precreate err {j}")
        return j["uploadid"]

    @retry(max_retry=3)
    def _upload_chunk(self, access_token: str, uploadid: str, remote_path: str, chunk_data, seq: int, local_md5: str):
        url = "https://d.pcs.baidu.com/rest/2.0/pcs/superfile2"
        encoded_path = self._encode_remote_path(remote_path)
        # ✅ 重点修复：增加 type=tmpfile
        params = {
            "method": "upload",
            "access_token": access_token,
            "uploadid": uploadid,
            "path": encoded_path,
            "partseq": seq,
            "type": "tmpfile"
        }
        files = {"file": chunk_data}
        if self.DEBUG:
            logger.debug(f"[upload_chunk DEBUG] seq={seq}, local_md5={local_md5}, url={url}, params={params}")
        r = requests.post(url, params=params, files=files, headers=self.HEADERS, timeout=60)
        j = self.safe_json(r)
        if j.get("md5") != local_md5:
            raise StorageError(f"分片{seq} md5不一致！本地:{local_md5}, 云端返回:{j.get('md5')}")
        return True

    @retry(max_retry=3)
    def _commit(self, access_token: str, uploadid: str, remote_path: str, file_size: int, block_list: list):
        url = "https://pan.baidu.com/rest/2.0/xpan/file"
        params = {"method": "create", "access_token": access_token}
        data = {
            "path": remote_path,
            "uploadid": uploadid,
            "size": file_size,
            "isdir": 0,
            "block_list": json.dumps(block_list)
        }
        if self.DEBUG:
            logger.debug(f"[commit DEBUG] url={url}, params={params}, data={data}")
        r = requests.post(url, params=params, data=data, headers=self.HEADERS, timeout=20)
        j = self.safe_json(r)
        if j.get("errno") != 0:
            raise StorageError(f"commit err {j}")
        return True

    def save(self, local_file_path: str, rel_path: str, file_record: FileRecord) -> bool:
        access_token = self.get_valid_access_token()
        if not access_token:
            return False
        raw_remote = f"{self.remote_root}/{rel_path}"
        remote_path = self.clean_remote_path(raw_remote)
        logger.info(f"原始组装路径:{raw_remote}, 清洗后网盘路径:{remote_path}")

        parent_dir, _ = self.split_remote_path(remote_path)
        self._mkdir(access_token, parent_dir)

        remote_md5 = self._get_remote_file_md5(access_token, remote_path)
        if remote_md5 is not None:
            if remote_md5 == file_record.filehash:
                logger.info(f"百度网盘校验md5一致，跳过上传：{remote_path} md5={remote_md5}")
                return True
            else:
                # 同名、md5不一致：冲突！这里策略：告警，不覆盖，直接返回
                logger.warning(f"【冲突警告】路径已存在但是md5不一致！path={remote_path} 云端md5={remote_md5} 入库md5={file_record.filehash}")
                return False


        local_fp = Path(local_file_path)
        file_size = local_fp.stat().st_size
        logger.info(f"开始百度网盘上传：{remote_path} size={file_size}")

        block_list, chunks = self.get_file_block_list(local_file_path)
        logger.info(f"分片总数：{len(chunks)}")

        uploadid = self._precreate(access_token, remote_path, file_size, block_list)
        if not uploadid:
            return False

        for seq, (chunk, md5) in enumerate(zip(chunks, block_list)):
            access_token = self.get_valid_access_token()
            if not access_token:
                return False
            self._upload_chunk(access_token, uploadid, remote_path, chunk, seq, md5)
            logger.info(f"百度网盘分片 {seq} md5={md5} 上传完成")

        access_token = self.get_valid_access_token()
        ok = self._commit(access_token, uploadid, remote_path, file_size, block_list)
        if ok:
            logger.info(f"百度网盘上传成功 {remote_path}")
            return True
        return False
