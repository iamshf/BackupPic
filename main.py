import click
from cli import scan_cli, check_cli, repair_cli
from core.db import create_all_tables

@click.group()
def cli():
    pass

cli.add_command(scan_cli)
cli.add_command(check_cli)
cli.add_command(repair_cli)

if __name__ == "__main__":
    create_all_tables()
    cli()
