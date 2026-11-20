import click
from cli import archive_cmd, check_cmd, retry_failed_cmd

@click.group()
def cli():
    pass

cli.add_command(archive_cmd)
cli.add_command(check_cmd)
cli.add_command(retry_failed_cmd)

if __name__ == "__main__":
    cli()
