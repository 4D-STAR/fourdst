# fourdst/cli/bundle/clear.py
import typer
import yaml
import zipfile
from pathlib import Path
import tempfile
import shutil

def bundle_clear(
    bundle_path: Path = typer.Argument(..., help="The path to the .fbundle file to clear.", exists=True, readable=True, writable=True)
):
    """
    Removes all compiled binaries from a bundle, leaving only the source distributions.
    """
    typer.echo(f"--- Clearing binaries from bundle: {bundle_path.name} ---")

    try:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            
            # 1. Unpack the bundle
            with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
                bundle_zip.extractall(temp_dir)

            # 2. Read the manifest
            manifest_path = temp_dir / "manifest.yaml"
            if not manifest_path.is_file():
                typer.secho("Error: Bundle is invalid. Missing manifest.yaml.", fg=typer.colors.RED)
                raise typer.Exit(code=1)
            
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)

            # 3. Clear binaries and signatures
            typer.echo("Clearing binaries and signature information...")
            manifest.pop('bundleAuthorKeyFingerprint', None)
            manifest.pop('checksums', None)

            for plugin_name, plugin_data in manifest.get('bundlePlugins', {}).items():
                if 'binaries' in plugin_data:
                    plugin_data['binaries'] = []
            
            # 4. Delete the binaries directory and signature file
            bin_dir = temp_dir / "bin"
            if bin_dir.is_dir():
                shutil.rmtree(bin_dir)
                typer.echo("  - Removed 'bin/' directory.")

            sig_file = temp_dir / "manifest.sig"
            if sig_file.is_file():
                sig_file.unlink()
                typer.echo("  - Removed 'manifest.sig'.")

            # 5. Write the updated manifest
            with open(manifest_path, 'w') as f:
                yaml.dump(manifest, f, sort_keys=False)

            # 6. Repack the bundle
            typer.echo("Repacking the bundle...")
            with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
                for file_path in temp_dir.rglob('*'):
                    if file_path.is_file():
                        bundle_zip.write(file_path, file_path.relative_to(temp_dir))

            typer.secho(f"\n✅ Bundle '{bundle_path.name}' has been cleared of all binaries.", fg=typer.colors.GREEN)

    except Exception as e:
        typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
