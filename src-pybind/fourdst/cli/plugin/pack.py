# fourdst/cli/plugin/pack.py
import typer
from pathlib import Path

from fourdst.core.plugin import validate_bundle_directory, pack_bundle_directory


def plugin_pack(
    folder_path: Path = typer.Argument(..., help="The directory to pack into a bundle.", exists=True, file_okay=False, dir_okay=True, readable=True),
    name: str = typer.Option(None, "--name", "-n", help="The name for the output bundle file (without extension). Defaults to the folder name.")
):
    """
    Validates and packs a directory into a .fbundle archive.
    """
    typer.echo(f"--- Validating Bundle Directory: {folder_path.resolve()} ---")
    
    # Validate using core function
    validation_result = validate_bundle_directory(folder_path)
    if not validation_result['success']:
        typer.secho(f"Error during validation: {validation_result['error']}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    validation_errors = validation_result['data']['errors']
    if validation_errors:
        typer.secho("Validation Failed. The following issues were found:", fg=typer.colors.RED, bold=True)
        for error in validation_errors:
            typer.echo(f"  - {error}")
        raise typer.Exit(code=1)
    
    typer.secho("✅ Validation Successful.", fg=typer.colors.GREEN)
    typer.echo("\n--- Packing Bundle ---")

    output_name = name if name else folder_path.name
    if folder_path.parent.exists():
        typer.secho(f"Warning: Output file {folder_path.parent / f'{output_name}.fbundle'} will be created/overwritten.", fg=typer.colors.YELLOW)

    # Pack using core function
    output_config = {
        'name': output_name,
        'output_dir': folder_path.parent
    }
    
    pack_result = pack_bundle_directory(folder_path, output_config)
    if not pack_result['success']:
        typer.secho(f"An unexpected error occurred during packing: {pack_result['error']}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Display results
    pack_data = pack_result['data']
    typer.echo(f"  Added {pack_data['files_packed']} files to bundle")
    typer.secho(f"\n✅ Successfully created bundle: {pack_data['output_path']}", fg=typer.colors.GREEN, bold=True)

    # Final status report
    if pack_data['is_signed']:
        typer.secho("Bundle Status: ✅ SIGNED", fg=typer.colors.GREEN)
    else:
        typer.secho("Bundle Status: 🟡 UNSIGNED", fg=typer.colors.YELLOW)
