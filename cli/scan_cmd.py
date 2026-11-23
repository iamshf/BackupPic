import click
from sqlalchemy.orm import Session
from core.db import get_db
from services.backup_service import BackupService

@click.command("scan")
def scan_cli():
    db: Session = next(get_db())
    svc = BackupService(db)
    svc.scan_and_backup()
