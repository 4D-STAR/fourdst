# fourdst/cli/plugin/extract.py
import typer
from pathlib import Path

from fourdst.core.plugin import extract_plugin_from_bundle

def plugin_extract(
    plugin_name: str = typer.Argument(..., help="The name of the plugin to extract."),
    bundle_path: Path = typer.Argument(..., help="The path to the .fbundle file.", exists=True, readable=True),
    output_dir: Path = typer.Option(
        Path("."), 
        "--out", "-o", 
        help="The directory to extract the plugin source to. Defaults to the current directory.",
        file_okay=False, 
        dir_okay=True, 
        writable=True,
        resolve_path=True
    )
):
    """
    Extracts a plugin's source code from a bundle.
    """
    typer.echo(f"Opening bundle: {bundle_path.name}")
    
    # Extract using core function
    extract_result = extract_plugin_from_bundle(bundle_path, plugin_name, output_dir)
    if not extract_result['success']:
        typer.secho(f"Error: {extract_result['error']}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Display results
    extract_data = extract_result['data']
    final_destination = Path(extract_data['output_path'])
    
    if final_destination.exists():
        typer.secho(f"Warning: Output directory '{final_destination}' already existed. Files may have been overwritten.", fg=typer.colors.YELLOW)

    typer.echo(f"Extracting '{plugin_name}' source to '{final_destination}'...")
    typer.secho(f"\n✅ Plugin '{plugin_name}' extracted successfully.", fg=typer.colors.GREEN)
