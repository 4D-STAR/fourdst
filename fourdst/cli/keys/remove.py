# fourdst/cli/keys/remove.py
import typer
import questionary
from pathlib import Path
import hashlib

from fourdst.cli.common.config import LOCAL_TRUST_STORE_PATH

def get_key_fingerprint(key_path: Path) -> str:
    """Generates a SHA256 fingerprint for a public key."""
    pub_key_bytes = key_path.read_bytes()
    # Assuming OpenSSH format, the fingerprint is based on the raw public key bytes
    # For simplicity, we'll hash the whole file content.
    return "sha256:" + hashlib.sha256(pub_key_bytes).hexdigest()

def keys_remove(
    key_path: Path = typer.Argument(None, help="Path to the public key file to remove.", exists=True, readable=True)
):
    """Removes a single public key from the local trust store."""
    if not LOCAL_TRUST_STORE_PATH.exists():
        typer.secho("Trust store not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if key_path:
        # Remove by content matching
        target_content = key_path.read_bytes()
        key_removed = False
        for source_dir in LOCAL_TRUST_STORE_PATH.iterdir():
            if source_dir.is_dir():
                for pub_key in source_dir.glob("*.pub"):
                    if pub_key.read_bytes() == target_content:
                        pub_key.unlink()
                        typer.secho(f"✅ Removed key '{pub_key.name}' from source '{source_dir.name}'.", fg=typer.colors.GREEN)
                        key_removed = True
        if not key_removed:
            typer.secho("No matching key found to remove.", fg=typer.colors.YELLOW)
    else:
        # Interactive removal
        all_keys = []
        for source_dir in LOCAL_TRUST_STORE_PATH.iterdir():
            if source_dir.is_dir():
                for pub_key in source_dir.glob("*.pub"):
                    all_keys.append(pub_key)
        
        if not all_keys:
            typer.echo("No keys to remove.")
            raise typer.Exit()

        choices = [
            {
                "name": f"{key.relative_to(LOCAL_TRUST_STORE_PATH)} ({get_key_fingerprint(key)})",
                "value": key
            } for key in all_keys
        ]
        
        selected_to_remove = questionary.checkbox("Select keys to remove:", choices=choices).ask()

        if selected_to_remove:
            for key_to_remove in selected_to_remove:
                key_to_remove.unlink()
                typer.secho(f"✅ Removed key '{key_to_remove.name}'.", fg=typer.colors.GREEN)
