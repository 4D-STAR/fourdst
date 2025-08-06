# fourdst/cli/plugin/pack.py
import typer
import sys
import yaml
import zipfile
from pathlib import Path

from fourdst.cli.common.utils import calculate_sha256

def _validate_bundle_directory(directory: Path) -> list[str]:
    """
    Validates that a directory has the structure of a valid bundle.
    Returns a list of error strings. An empty list means success.
    """
    errors = []
    manifest_path = directory / "manifest.yaml"

    if not manifest_path.is_file():
        return ["Error: Missing 'manifest.yaml' in the root of the directory."]

    try:
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"Error: Invalid YAML in manifest.yaml: {e}"]

    # 1. Check that all files referenced in the manifest exist
    for plugin_name, plugin_data in manifest.get('bundlePlugins', {}).items():
        sdist_info = plugin_data.get('sdist', {})
        if sdist_info:
            sdist_path = sdist_info.get('path')
            if sdist_path and not (directory / sdist_path).is_file():
                errors.append(f"Missing sdist file for '{plugin_name}': {sdist_path}")
        
        for binary in plugin_data.get('binaries', []):
            binary_path = binary.get('path')
            if binary_path and not (directory / binary_path).is_file():
                errors.append(f"Missing binary file for '{plugin_name}': {binary_path}")
            
            # 2. If checksums exist, validate them
            expected_checksum = binary.get('checksum')
            if binary_path and expected_checksum:
                file_to_check = directory / binary_path
                if file_to_check.is_file():
                    actual_checksum = "sha256:" + calculate_sha256(file_to_check)
                    if actual_checksum != expected_checksum:
                        errors.append(f"Checksum mismatch for '{binary_path}'")

    return errors


def plugin_pack(
    folder_path: Path = typer.Argument(..., help="The directory to pack into a bundle.", exists=True, file_okay=False, dir_okay=True, readable=True),
    name: str = typer.Option(None, "--name", "-n", help="The name for the output bundle file (without extension). Defaults to the folder name.")
):
    """
    Validates and packs a directory into a .fbundle archive.
    """
    typer.echo(f"--- Validating Bundle Directory: {folder_path.resolve()} ---")
    
    validation_errors = _validate_bundle_directory(folder_path)
    
    if validation_errors:
        typer.secho("Validation Failed. The following issues were found:", fg=typer.colors.RED, bold=True)
        for error in validation_errors:
            typer.echo(f"  - {error}")
        raise typer.Exit(code=1)
    
    typer.secho("✅ Validation Successful.", fg=typer.colors.GREEN)
    typer.echo("\n--- Packing Bundle ---")

    output_name = name if name else folder_path.name
    output_path = folder_path.parent / f"{output_name}.fbundle"

    if output_path.exists():
        typer.secho(f"Warning: Output file {output_path} already exists and will be overwritten.", fg=typer.colors.YELLOW)

    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
            for file_to_add in folder_path.rglob('*'):
                if file_to_add.is_file():
                    arcname = file_to_add.relative_to(folder_path)
                    bundle_zip.write(file_to_add, arcname)
                    typer.echo(f"  Adding: {arcname}")
        
        typer.secho(f"\n✅ Successfully created bundle: {output_path.resolve()}", fg=typer.colors.GREEN, bold=True)

        # Final status report
        with open(folder_path / "manifest.yaml", 'r') as f:
            manifest = yaml.safe_load(f)
        
        is_signed = 'bundleAuthorKeyFingerprint' in manifest and (folder_path / "manifest.sig").exists()
        if is_signed:
            typer.secho("Bundle Status: ✅ SIGNED", fg=typer.colors.GREEN)
        else:
            typer.secho("Bundle Status: 🟡 UNSIGNED", fg=typer.colors.YELLOW)

    except Exception as e:
        typer.secho(f"An unexpected error occurred during packing: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
