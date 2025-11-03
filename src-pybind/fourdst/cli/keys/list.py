# fourdst/cli/keys/list.py
import typer
from fourdst.core.keys import list_keys

def keys_list():
    """Lists all trusted public keys."""
    result = list_keys()
    
    if not result["success"]:
        typer.secho(f"Error: {result['error']}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    if result["total_count"] == 0:
        typer.echo("No trusted keys found.")
        return
    
    typer.echo(f"Found {result['total_count']} trusted keys:\n")
    
    for source_name, keys in result["keys"].items():
        typer.secho(f"--- Source: {source_name} ---", bold=True)
        for key_info in keys:
            typer.echo(f"  - {key_info['name']}")
            typer.echo(f"    Fingerprint: {key_info['fingerprint']}")
            typer.echo(f"    Size: {key_info['size_bytes']} bytes")
        typer.echo()  # Empty line between sources
