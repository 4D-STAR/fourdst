# fourdst/cli/keys/remote/remove.py
import typer
import json
from pathlib import Path
from fourdst.cli.common.config import FOURDST_CONFIG_DIR

KEY_REMOTES_CONFIG = FOURDST_CONFIG_DIR / "key_remotes.json"

def remote_remove(
    name: str = typer.Argument(..., help="The name of the remote to remove.")
):
    """Removes a remote key source."""
    if not KEY_REMOTES_CONFIG.exists():
        typer.secho("Error: No remotes configured.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    with open(KEY_REMOTES_CONFIG, 'r') as f:
        config = json.load(f)

    original_len = len(config['remotes'])
    config['remotes'] = [r for r in config['remotes'] if r['name'] != name]

    if len(config['remotes']) == original_len:
        typer.secho(f"Error: Remote '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    with open(KEY_REMOTES_CONFIG, 'w') as f:
        json.dump(config, f, indent=2)
        
    typer.secho(f"✅ Remote '{name}' removed.", fg=typer.colors.GREEN)
