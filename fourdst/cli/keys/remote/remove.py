# fourdst/cli/keys/remote/remove.py
import typer
from fourdst.core.keys import remove_remote_source

def remote_remove(
    name: str = typer.Argument(..., help="The name of the remote to remove.")
):
    """Removes a remote key source."""
    result = remove_remote_source(name)
    
    if result["success"]:
        typer.secho(f"✅ Remote '{result['name']}' removed.", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Error: {result['error']}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
