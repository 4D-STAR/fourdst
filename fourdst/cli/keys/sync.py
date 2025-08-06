# fourdst/cli/keys/sync.py
import typer
import shutil
import json
from pathlib import Path
import questionary

from fourdst.cli.common.config import FOURDST_CONFIG_DIR, LOCAL_TRUST_STORE_PATH

KEY_REMOTES_CONFIG = FOURDST_CONFIG_DIR / "key_remotes.json"
REMOTES_DIR = LOCAL_TRUST_STORE_PATH / "remotes"

keys_app = typer.Typer()

@keys_app.command("sync")
def keys_sync():
    """
    Syncs the local trust store with all configured remote Git repositories.
    """
    if not KEY_REMOTES_CONFIG.exists():
        typer.secho("No remotes configured. Use 'fourdst-cli keys remote add' to add one.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    with open(KEY_REMOTES_CONFIG, 'r') as f:
        config = json.load(f)
    
    remotes = config.get("remotes", [])
    if not remotes:
        typer.secho("No remotes configured.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    REMOTES_DIR.mkdir(parents=True, exist_ok=True)
    
    remotes_to_remove = []

    for remote in remotes:
        name = remote['name']
        url = remote['url']
        remote_path = REMOTES_DIR / name
        
        typer.secho(f"--- Syncing remote '{name}' from {url} ---", bold=True)
        
        try:
            if remote_path.exists():
                run_command(["git", "pull"], cwd=remote_path)
            else:
                run_command(["git", "clone", "--depth", "1", url, str(remote_path)])
            
            # Clean up non-public key files
            for item in remote_path.iterdir():
                if item.is_file() and item.suffix != '.pub':
                    item.unlink()
            
            typer.secho(f"✅ Sync successful for '{name}'.", fg=typer.colors.GREEN)

        except Exception as e:
            typer.secho(f"⚠️ Failed to sync remote '{name}': {e}", fg=typer.colors.YELLOW)
            if questionary.confirm(f"Do you want to remove the remote '{name}'?").ask():
                remotes_to_remove.append(name)

    if remotes_to_remove:
        config['remotes'] = [r for r in config['remotes'] if r['name'] not in remotes_to_remove]
        with open(KEY_REMOTES_CONFIG, 'w') as f:
            json.dump(config, f, indent=2)
        typer.secho(f"Removed failing remotes: {', '.join(remotes_to_remove)}", fg=typer.colors.YELLOW)

