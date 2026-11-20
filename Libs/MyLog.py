import logging

def init_logger(log_file: str, log_level: str):
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger("archive")
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    # 控制台
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    # 文件
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger