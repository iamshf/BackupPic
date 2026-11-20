import os
import hashlib
import magic
from datetime import datetime

def file_hash(file_path, hash_method='sha256'):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"{file_path} 不存在")
    hash_func = getattr(hashlib, hash_method)()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def calc_sha256(file_path: str, chunk_size=65536) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while b := f.read(chunk_size):
            h.update(b)
    return h.hexdigest()

def get_file_mime(file_path: str) -> str:
    try:
        return magic.from_file(file_path, mime=True)
    except Exception:
        return "application/octet-stream"

def get_file_ctime_ts(file_path: str) -> int:
    return int(os.path.getctime(file_path))

def get_file_mtime_ts(file_path: str) -> int:
    return int(os.path.getmtime(file_path))

def ts_to_path_key(ts: int) -> str:
    dt = datetime.fromtimestamp(ts)
    return dt.strftime("%Y/%m/%d")

def make_safe_dst_name(original_name: str, sha256_hash: str) -> str:
    base, ext = os.path.splitext(original_name)
    short_hash = sha256_hash[:8]
    return f"{base}_{short_hash}{ext}"
