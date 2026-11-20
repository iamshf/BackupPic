import click
from src.common.config_loader import load_config
from src.common.logger_setup import init_logger
from src.db.base import get_engine, get_session_factory, DbSessionCtx
from src.db.base import Base
from src.services.archive_service import ArchiveService
from src.services.storage import get_storage_driver

@click.command(name="archive")
def archive_cmd():
    cfg = load_config()
    logger = init_logger(cfg["log_file"], cfg["log_level"])
    engine = get_engine(cfg["db_url"])
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(engine)
    storage = get_storage_driver(cfg["storage_driver"], cfg["target_root"], cfg)
    svc = ArchiveService(storage, cfg["batch_size"])

    with DbSessionCtx(session_factory) as sess:
        svc.run_scan(sess, cfg["source_dir"])
