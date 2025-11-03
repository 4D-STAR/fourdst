# fourdst/cli/bundle/clear.py
import typer
from pathlib import Path

from fourdst.core.bundle import clear_bundle

def bundle_clear(
    bundle_path: Path = typer.Argument(
        ..., 
        help="The path to the .fbundle file to clear.", 
        exists=True, 
        readable=True, 
        writable=True
    )
):
    """
    Removes all compiled binaries and signatures from a bundle.
    """
    try:
        clear_bundle(bundle_path, progress_callback=typer.echo)
    except Exception as e:
        typer.secho(f"An error occurred while clearing the bundle: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
