from pathlib import Path
import mimetypes
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

def get_file_size(filepath: str) -> int:
    return Path(filepath).stat().st_size

def get_ext_name(filepath: str) -> str:
    suf = Path(filepath).suffix.lower()
    return suf

def guess_mimetype(filepath: str) -> str:
    if HAS_MAGIC:
        try:
            return magic.from_file(filepath, mime=True)
        except Exception:
            pass
    mt, _ = mimetypes.guess_type(filepath)
    return mt if mt else "application/octet-stream"
