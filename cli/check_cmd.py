import click
from src.common.config_loader import load_config
from src.common.logger_setup import init_logger
from src.db.base import get_engine, get_session_factory, DbSessionCtx
from src.services.check_service import CheckService
from src.services.storage import get_storage_driver

@click.command(name="check")
def check_cmd():
    cfg = load_config()
    logger = init_logger(cfg["log_file"], cfg["log_level"])
    engine = get_engine(cfg["db_url"])
    session_factory = get_session_factory(engine)
    storage = get_storage_driver(cfg["storage_driver"], cfg["target_root"], cfg)
    svc = CheckService(storage)

    with DbSessionCtx(session_factory) as sess:
        svc.run_check(sess)
