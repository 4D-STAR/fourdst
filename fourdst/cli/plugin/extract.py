# fourdst/cli/plugin/extract.py
import typer
import yaml
import zipfile
from pathlib import Path
import tempfile
import shutil

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
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            
            # 1. Unpack the main bundle
            typer.echo(f"Opening bundle: {bundle_path.name}")
            with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
                bundle_zip.extractall(temp_dir)

            # 2. Read the manifest
            manifest_path = temp_dir / "manifest.yaml"
            if not manifest_path.exists():
                typer.secho("Error: Bundle is invalid. Missing manifest.yaml.", fg=typer.colors.RED)
                raise typer.Exit(code=1)
            
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)

            # 3. Find the plugin and its sdist
            plugin_data = manifest.get('bundlePlugins', {}).get(plugin_name)
            if not plugin_data:
                typer.secho(f"Error: Plugin '{plugin_name}' not found in the bundle.", fg=typer.colors.RED)
                available_plugins = list(manifest.get('bundlePlugins', {}).keys())
                if available_plugins:
                    typer.echo("Available plugins are: " + ", ".join(available_plugins))
                raise typer.Exit(code=1)

            sdist_info = plugin_data.get('sdist')
            if not sdist_info or 'path' not in sdist_info:
                typer.secho(f"Error: Source distribution (sdist) not found for plugin '{plugin_name}'.", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            sdist_path_in_bundle = temp_dir / sdist_info['path']
            if not sdist_path_in_bundle.is_file():
                typer.secho(f"Error: sdist file '{sdist_info['path']}' is missing from the bundle archive.", fg=typer.colors.RED)
                raise typer.Exit(code=1)

            # 4. Extract the sdist to the final output directory
            final_destination = output_dir / plugin_name
            if final_destination.exists():
                 typer.secho(f"Warning: Output directory '{final_destination}' already exists. Files may be overwritten.", fg=typer.colors.YELLOW)
            else:
                final_destination.mkdir(parents=True)

            typer.echo(f"Extracting '{plugin_name}' source to '{final_destination.resolve()}'...")
            with zipfile.ZipFile(sdist_path_in_bundle, 'r') as sdist_zip:
                sdist_zip.extractall(final_destination)

            typer.secho(f"\n✅ Plugin '{plugin_name}' extracted successfully.", fg=typer.colors.GREEN)

    except zipfile.BadZipFile:
        typer.secho(f"Error: '{bundle_path}' is not a valid bundle (zip) file.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
