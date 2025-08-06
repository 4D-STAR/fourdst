# fourdst/cli/bundle/fill.py

import typer
import shutil
import datetime
import yaml
import zipfile
from pathlib import Path
import questionary
import subprocess
import sys
import traceback

try:
    import docker
except ImportError:
    docker = None # Docker is an optional dependency for the 'fill' command

from rich.console import Console
from rich.panel import Panel

console = Console()

from fourdst.cli.common.utils import get_available_build_targets, _build_plugin_in_docker, _build_plugin_for_target

bundle_app = typer.Typer()

@bundle_app.command("fill")
def bundle_fill(bundle_path: Path = typer.Argument(..., help="The .fbundle file to fill with new binaries.", exists=True)):
    """
    Builds new binaries for the current host or cross-targets from the bundle's source.
    """
    staging_dir = Path(f"temp_fill_{bundle_path.stem}")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    
    try:
        # 1. Unpack and load manifest
        with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
            bundle_zip.extractall(staging_dir)

        manifest_path = staging_dir / "manifest.yaml"
        if not manifest_path.exists():
            typer.secho("Error: Bundle is invalid. Missing manifest.yaml.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)

        # 2. Find available targets and missing binaries
        available_targets = get_available_build_targets()
        build_options = []
        
        for plugin_name, plugin_data in manifest.get('bundlePlugins', {}).items():
            if "sdist" not in plugin_data:
                continue # Cannot build without source
            
            existing_abis = {b['platform']['abi_signature'] for b in plugin_data.get('binaries', [])}
            
            for target in available_targets:
                # Use a more descriptive name for the choice
                if target.get('docker_image', None):
                    display_name = f"Docker: {target['docker_image']}"
                elif target.get('cross_file', None):
                    display_name = f"Cross: {Path(target['cross_file']).name}"
                else:
                    display_name = f"Native: {target['abi_signature']} (Local System)"

                if target['abi_signature'] not in existing_abis:
                    build_options.append({
                        "name": f"Build '{plugin_name}' for {display_name}",
                        "plugin_name": plugin_name,
                        "target": target
                    })
        
        if not build_options:
            typer.secho("✅ Bundle is already full for all available build targets.", fg=typer.colors.GREEN)
            raise typer.Exit()
            
        # 3. Prompt user to select which targets to build
        choices = [opt['name'] for opt in build_options]
        selected_builds = questionary.checkbox(
            "Select which missing binaries to build:", 
            choices=choices
        ).ask()
        
        if not selected_builds:
            typer.echo("No binaries selected to build. Exiting.")
            raise typer.Exit()
            
        # 4. Build selected targets
        for build_name in selected_builds:
            build_job = next(opt for opt in build_options if opt['name'] == build_name)
            plugin_name = build_job['plugin_name']
            target = build_job['target']
            
            typer.secho(f"\nBuilding {plugin_name} for target '{build_name}'...", bold=True)
            
            sdist_zip_path = staging_dir / manifest['bundlePlugins'][plugin_name]['sdist']['path']
            build_temp_dir = staging_dir / f"build_{plugin_name}"

            try:
                if target['docker_image']:
                    if not docker:
                        typer.secho("Error: Docker is not installed. Please install Docker to build this target.", fg=typer.colors.RED)
                        continue
                    compiled_lib, final_target = _build_plugin_in_docker(sdist_zip_path, build_temp_dir, target, plugin_name)
                else:
                    compiled_lib, final_target = _build_plugin_for_target(sdist_zip_path, build_temp_dir, target)
                
                # Add new binary to bundle
                abi_tag = final_target["abi_signature"]
                base_name = compiled_lib.stem
                ext = compiled_lib.suffix
                triplet = final_target["triplet"]
                tagged_filename = f"{base_name}.{triplet}.{abi_tag}{ext}"
                
                binaries_dir = staging_dir / "bin"
                binaries_dir.mkdir(exist_ok=True)
                staged_lib_path = binaries_dir / tagged_filename
                shutil.move(compiled_lib, staged_lib_path)
                
                # Update manifest
                new_binary_entry = {
                    "platform": {
                        "triplet": final_target["triplet"],
                        "abi_signature": abi_tag,
                        "arch": final_target["arch"]
                    },
                    "path": staged_lib_path.relative_to(staging_dir).as_posix(),
                    "compiledOn": datetime.datetime.now().isoformat()
                }
                manifest['bundlePlugins'][plugin_name]['binaries'].append(new_binary_entry)
                typer.secho(f"  -> Successfully built and staged {tagged_filename}", fg=typer.colors.GREEN)

            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                typer.secho(f"  -> Failed to build {plugin_name} for target '{build_name}': {e}", fg=typer.colors.RED)
                
                tb_str = traceback.format_exc()
                console.print(Panel(
                    tb_str,
                    title="Traceback",
                    border_style="yellow",
                    expand=False
                ))
                
            finally:
                if build_temp_dir.exists():
                    shutil.rmtree(build_temp_dir)

        # 5. Repackage the bundle
        # Invalidate any old signature
        if "bundleAuthorKeyFingerprint" in manifest:
            del manifest["bundleAuthorKeyFingerprint"]
            if (staging_dir / "manifest.sig").exists():
                (staging_dir / "manifest.sig").unlink()
            typer.secho("\n⚠️ Bundle signature has been invalidated by this operation. Please re-sign the bundle.", fg=typer.colors.YELLOW)

        with open(manifest_path, 'w') as f:
            yaml.dump(manifest, f, sort_keys=False)
            
        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
            for file_path in staging_dir.rglob('*'):
                if file_path.is_file():
                    bundle_zip.write(file_path, file_path.relative_to(staging_dir))
        
        typer.secho(f"\n✅ Bundle '{bundle_path.name}' has been filled successfully.", fg=typer.colors.GREEN)

    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
