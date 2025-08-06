# fourdst/cli/keys/remote/add.py
import typer
import json
from pathlib import Path
from fourdst.cli.common.config import FOURDST_CONFIG_DIR

KEY_REMOTES_CONFIG = FOURDST_CONFIG_DIR / "key_remotes.json"

def remote_add(
    url: str = typer.Argument(..., help="The URL of the Git repository."),
    name: str = typer.Argument(..., help="A local name for the remote.")
):
    """Adds a new remote key source."""
    FOURDST_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    if KEY_REMOTES_CONFIG.exists():
        with open(KEY_REMOTES_CONFIG, 'r') as f:
            config = json.load(f)
    else:
        config = {"remotes": []}

    if any(r['name'] == name for r in config['remotes']):
        typer.secho(f"Error: Remote with name '{name}' already exists.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    config['remotes'].append({"name": name, "url": url})

    with open(KEY_REMOTES_CONFIG, 'w') as f:
        json.dump(config, f, indent=2)
    
    typer.secho(f"✅ Remote '{name}' added.", fg=typer.colors.GREEN)
