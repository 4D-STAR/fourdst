# fourdst/cli/keys/remote/list.py
import typer
from fourdst.core.keys import get_remote_sources

def remote_list():
    """Lists all configured remote key sources."""
    result = get_remote_sources()
    
    if not result["success"]:
        typer.secho(f"Error: {result['error']}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    if not result["remotes"]:
        typer.echo("No remotes configured.")
        return
        
    typer.secho("Configured Key Remotes:", bold=True)
    for remote in result["remotes"]:
        status = "✅" if remote["exists"] else "❌"
        typer.echo(f"  {status} {remote['name']}: {remote['url']}")
        if remote["exists"]:
            typer.echo(f"      Keys: {remote['keys_count']}")
        else:
            typer.echo(f"      Status: Not synced yet")
