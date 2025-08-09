# fourdst/cli/bundle/create.py

import typer
from pathlib import Path
import sys

from fourdst.core.bundle import create_bundle

def bundle_create(
    plugin_dirs: list[Path] = typer.Argument(..., help="A list of plugin project directories to include.", exists=True, file_okay=False),
    output_bundle: Path = typer.Option("bundle.fbundle", "--out", "-o", help="The path for the output bundle file."),
    bundle_name: str = typer.Option("MyPluginBundle", "--name", help="The name of the bundle."),
    bundle_version: str = typer.Option("0.1.0", "--ver", help="The version of the bundle."),
    bundle_author: str = typer.Option("Unknown", "--author", help="The author of the bundle."),
    bundle_comment: str = typer.Option(None, "--comment", help="A comment to embed in the bundle."),
    target_macos_version: str = typer.Option(None, "--target-macos-version", help="The minimum macOS version to target (e.g., '12.0').")
):
    """
    Builds and packages one or more plugin projects into a single .fbundle file.
    """
    def progress_callback(message):
        typer.secho(message, fg=typer.colors.BRIGHT_BLUE)

    try:
        create_bundle(
            plugin_dirs=plugin_dirs,
            output_bundle=output_bundle,
            bundle_name=bundle_name,
            bundle_version=bundle_version,
            bundle_author=bundle_author,
            bundle_comment=bundle_comment,
            target_macos_version=target_macos_version,
            progress_callback=progress_callback
        )
    except Exception as e:
        typer.secho(f"Error creating bundle: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
