# fourdst/cli/keys/remote/list.py
import typer
import json
from pathlib import Path
from fourdst.cli.common.config import FOURDST_CONFIG_DIR

KEY_REMOTES_CONFIG = FOURDST_CONFIG_DIR / "key_remotes.json"

def remote_list():
    """Lists all configured remote key sources."""
    if not KEY_REMOTES_CONFIG.exists():
        typer.echo("No remotes configured.")
        return

    with open(KEY_REMOTES_CONFIG, 'r') as f:
        config = json.load(f)

    if not config.get("remotes"):
        typer.echo("No remotes configured.")
        return
        
    typer.secho("Configured Key Remotes:", bold=True)
    for remote in config['remotes']:
        typer.echo(f"  - {remote['name']}: {remote['url']}")
