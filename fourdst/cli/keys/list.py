# fourdst/cli/keys/list.py
import typer
from pathlib import Path
from fourdst.cli.common.config import LOCAL_TRUST_STORE_PATH

def keys_list():
    """Lists all trusted public keys."""
    if not LOCAL_TRUST_STORE_PATH.exists():
        typer.echo("Trust store not found.")
        return

    keys_found = False
    for source_dir in LOCAL_TRUST_STORE_PATH.iterdir():
        if source_dir.is_dir():
            keys = list(source_dir.glob("*.pub"))
            if keys:
                keys_found = True
                typer.secho(f"\n--- Source: {source_dir.name} ---", bold=True)
                for key_file in keys:
                    typer.echo(f"  - {key_file.name}")
    
    if not keys_found:
        typer.echo("No trusted keys found.")
