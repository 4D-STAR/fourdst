# fourdst/cli/keys/remote/add.py
import typer
from fourdst.core.keys import add_remote_source

def remote_add(
    url: str = typer.Argument(..., help="The URL of the Git repository."),
    name: str = typer.Argument(..., help="A local name for the remote.")
):
    """Adds a new remote key source."""
    result = add_remote_source(name, url)
    
    if result["success"]:
        typer.secho(f"✅ Remote '{result['name']}' added.", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Error: {result['error']}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
