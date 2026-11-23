import logging
from pathlib import Path
from core.settings import settings

LOG_DIR = Path(__file__).parent.parent / settings.log_dir
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("file_backup")
logger.setLevel(settings.log_level)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

fh = logging.FileHandler(LOG_DIR / "backup.log", encoding="utf-8")
fh.setFormatter(formatter)
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(sh)
