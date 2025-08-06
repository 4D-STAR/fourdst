# fourdst/cli/keys/add.py
import typer
import shutil
from pathlib import Path
from fourdst.cli.common.config import LOCAL_TRUST_STORE_PATH

MANUAL_KEYS_DIR = LOCAL_TRUST_STORE_PATH / "manual"

def keys_add(
    key_path: Path = typer.Argument(..., help="Path to the public key file to add.", exists=True, readable=True)
):
    """Adds a single public key to the local trust store."""
    MANUAL_KEYS_DIR.mkdir(parents=True, exist_ok=True)
    
    destination = MANUAL_KEYS_DIR / key_path.name
    if destination.exists():
        # check content
        if destination.read_bytes() == key_path.read_bytes():
            typer.secho(f"Key '{key_path.name}' with same content already exists.", fg=typer.colors.YELLOW)
            return
    
    shutil.copy(key_path, destination)
    typer.secho(f"✅ Key '{key_path.name}' added to manual trust store.", fg=typer.colors.GREEN)
