import time
import logging
from functools import wraps

logger = logging.getLogger("archive")

class ArchiveError(Exception):
    """归档业务基础异常"""
    pass

class StorageError(ArchiveError):
    """存储异常（本地/云存储通用）"""
    pass

def retry(times: int = 3, delay: float = 2.0):
    """
    上传重试装饰器：只重试网络异常、5xx；4xx参数错误不重试
    :param times: 最大重试次数
    :param delay: 初始等待秒数，指数退避
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    if hasattr(e, "response") and getattr(e.response, "status_code", None):
                        status_code = e.response.status_code
                        if 400 <= status_code < 500:
                            raise StorageError(f"请求参数错误，不重试：{e}") from e
                    wait = delay * (2 ** attempt)
                    logger.warning(f"执行失败，准备重试 {attempt+1}/{times}, 等待 {wait:.1f}s, err: {e}")
                    time.sleep(wait)
            raise StorageError(f"重试 {times} 次后仍然失败") from last_err
        return wrapper
    return decorator
