# fourdst/cli/bundle/sign.py

import typer
from pathlib import Path

from fourdst.core.bundle import sign_bundle

def bundle_sign(
    bundle_path: Path = typer.Argument(..., help="The .fbundle file to sign.", exists=True),
    private_key: Path = typer.Option(..., "--key", "-k", help="Path to the author's private signing key.", exists=True)
):
    """
    Signs a bundle with an author's private key.
    """
    def progress_callback(message):
        typer.secho(message, fg=typer.colors.BRIGHT_BLUE)

    try:
        sign_bundle(
            bundle_path=bundle_path,
            private_key=private_key,
            progress_callback=progress_callback
        )
    except Exception as e:
        typer.secho(f"Error signing bundle: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
