# cli/check_cmd.py
import click
from sqlalchemy.orm import Session
from core.db import get_db
from repositories.file_repo import FileRecord

@click.command("check")
def check_cli():
    """一致性检查，统计失败数量"""
    db: Session = next(get_db())
    total = db.query(FileRecord).count()
    local_fail = db.query(FileRecord).filter(FileRecord.local_saved == 0).count()
    baidu_fail = db.query(FileRecord).filter(FileRecord.baidu_saved == 0).count()
    click.echo(f"总入库记录：{total}")
    click.echo(f"本地备份失败：{local_fail}")
    click.echo(f"百度网盘备份失败：{baidu_fail}")
