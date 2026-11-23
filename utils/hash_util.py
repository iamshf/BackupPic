import hashlib

def calc_sha256(filepath: str, chunk_size: int = 4*1024*1024) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()
