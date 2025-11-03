# fourdst/cli/keys/add.py
import typer
from pathlib import Path
from fourdst.core.keys import add_key

def keys_add(
    key_path: Path = typer.Argument(..., help="Path to the public key file to add.", exists=True, readable=True)
):
    """Adds a single public key to the local trust store."""
    result = add_key(key_path)
    
    if result["success"]:
        if result["already_existed"]:
            typer.secho(f"Key '{result['key_name']}' with same content already exists.", fg=typer.colors.YELLOW)
        else:
            typer.secho(f"✅ Key '{result['key_name']}' added to manual trust store.", fg=typer.colors.GREEN)
        typer.echo(f"Fingerprint: {result['fingerprint']}")
    else:
        typer.secho(f"Error: {result['error']}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
