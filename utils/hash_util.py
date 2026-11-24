import hashlib
import os

# def calc_sha256(filepath: str, chunk_size: int = 4*1024*1024) -> str:
#     h = hashlib.sha256()
#     with open(filepath, "rb") as f:
#         while chunk := f.read(chunk_size):
#             h.update(chunk)
#     return h.hexdigest()


def calc_file_hash(file_path , hash_method='sha256', chunk_size: int = 4*1024*1024) -> str:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"{file_path} 不存在")
    hash_func = getattr(hashlib, hash_method)()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            hash_func.update(chunk)
    return hash_func.hexdigest()
