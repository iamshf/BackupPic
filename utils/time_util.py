from pathlib import Path
import datetime

def get_file_create_time(filepath: str) -> datetime.datetime:
    fp = Path(filepath)
    stat_info = fp.stat()
    try:
        return datetime.datetime.fromtimestamp(stat_info.st_ctime)
    except Exception:
        return datetime.datetime.fromtimestamp(stat_info.st_mtime)
