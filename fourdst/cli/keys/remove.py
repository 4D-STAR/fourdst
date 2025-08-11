# fourdst/cli/keys/remove.py
import typer
import questionary
from pathlib import Path

from fourdst.core.keys import remove_key, list_keys

def keys_remove(
    key_path: Path = typer.Argument(None, help="Path to the public key file to remove.", exists=True, readable=True)
):
    """Removes a single public key from the local trust store."""
    if key_path:
        # Remove by path
        result = remove_key(str(key_path))
        
        if result["success"]:
            for removed_key in result["removed_keys"]:
                typer.secho(f"✅ Removed key '{removed_key['name']}' from source '{removed_key['source']}'.", fg=typer.colors.GREEN)
        else:
            typer.secho(f"Error: {result['error']}", fg=typer.colors.YELLOW)
    else:
        # Interactive removal
        keys_result = list_keys()
        
        if not keys_result["success"]:
            typer.secho(f"Error: {keys_result['error']}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        if keys_result["total_count"] == 0:
            typer.echo("No keys to remove.")
            raise typer.Exit()

        # Build choices for interactive selection
        choices = []
        for source_name, keys in keys_result["keys"].items():
            for key_info in keys:
                relative_path = f"{source_name}/{key_info['name']}"
                choice_name = f"{relative_path} ({key_info['fingerprint']})"
                choices.append({
                    "name": choice_name,
                    "value": key_info['fingerprint']  # Use fingerprint as identifier
                })
        
        selected_fingerprints = questionary.checkbox("Select keys to remove:", choices=choices).ask()

        if selected_fingerprints:
            for fingerprint in selected_fingerprints:
                result = remove_key(fingerprint)
                if result["success"]:
                    for removed_key in result["removed_keys"]:
                        typer.secho(f"✅ Removed key '{removed_key['name']}'.", fg=typer.colors.GREEN)
                else:
                    typer.secho(f"Error removing key: {result['error']}", fg=typer.colors.RED)
