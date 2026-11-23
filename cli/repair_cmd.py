# cli/repair_cmd.py
import click
from sqlalchemy.orm import Session
from core.db import get_db
from scripts.retry_failed import run_retry_failed

@click.command("repair")
@click.option("--target", "-t", type=click.Choice(["local", "baidupcs", "all"]), default="all", help="重试目标：local / baidupcs / all")
def repair_cli(target):
    """
    重试备份失败的文件
    --target local：只重试本地备份失败
    --target baidupcs：只重试百度网盘上传失败
    --target all：两者都重试（默认）
    """
    db: Session = next(get_db())
    run_retry_failed(db, target)
