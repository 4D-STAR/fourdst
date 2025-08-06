# fourdst/cli/bundle/create.py

import typer
import os
import sys
import shutil
import datetime
import yaml
import zipfile
from pathlib import Path

from fourdst.cli.common.utils import get_platform_identifier, run_command

bundle_app = typer.Typer()

@bundle_app.command("create")
def bundle_create(
    plugin_dirs: list[Path] = typer.Argument(..., help="A list of plugin project directories to include.", exists=True, file_okay=False),
    output_bundle: Path = typer.Option("bundle.fbundle", "--out", "-o", help="The path for the output bundle file."),
    bundle_name: str = typer.Option("MyPluginBundle", "--name", help="The name of the bundle."),
    bundle_version: str = typer.Option("0.1.0", "--ver", help="The version of the bundle."),
    bundle_author: str = typer.Option("Unknown", "--author", help="The author of the bundle.")
):
    """
    Builds and packages one or more plugin projects into a single .fbundle file.
    """
    staging_dir = Path("temp_bundle_staging")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir()

    # Get the host platform identifier, triggering detection if needed.
    host_platform = get_platform_identifier()

    manifest = {
        "bundleName": bundle_name,
        "bundleVersion": bundle_version,
        "bundleAuthor": bundle_author,
        "bundleComment": "Created with fourdst-cli",
        "bundledOn": datetime.datetime.now().isoformat(),
        "bundlePlugins": {}
    }
    
    print("Creating bundle...")
    for plugin_dir in plugin_dirs:
        plugin_name = plugin_dir.name
        print(f"--> Processing plugin: {plugin_name}")

        # 1. Build the plugin
        print(f"    - Compiling for host platform...")
        build_dir = plugin_dir / "builddir"
        if not build_dir.exists():
            run_command(["meson", "setup", "builddir"], cwd=plugin_dir)
        run_command(["meson", "compile", "-C", "builddir"], cwd=plugin_dir)

        # 2. Find the compiled artifact
        compiled_lib = next(build_dir.glob("lib*.so"), None) or next(build_dir.glob("lib*.dylib"), None)
        if not compiled_lib:
            print(f"Error: Could not find compiled library for {plugin_name} (expected lib*.so or lib*.dylib)", file=sys.stderr)
            raise typer.Exit(code=1)

        # 3. Package source code (sdist), respecting .gitignore
        print("    - Packaging source code (respecting .gitignore)...")
        sdist_path = staging_dir / f"{plugin_name}_src.zip"
        
        # Use git to list files, which automatically respects .gitignore
        git_check = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=plugin_dir, check=False)
        
        files_to_include = []
        if git_check.returncode == 0:
            # This is a git repo, use git to list files
            result = run_command(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=plugin_dir)
            files_to_include = [plugin_dir / f for f in result.stdout.strip().split('\n') if f]
        else:
            # Not a git repo, fall back to os.walk and warn the user
            typer.secho(f"    - Warning: '{plugin_dir.name}' is not a git repository. Packaging all files.", fg=typer.colors.YELLOW)
            for root, _, files in os.walk(plugin_dir):
                if 'builddir' in root:
                    continue
                for file in files:
                    files_to_include.append(Path(root) / file)

        with zipfile.ZipFile(sdist_path, 'w', zipfile.ZIP_DEFLATED) as sdist_zip:
            for file_path in files_to_include:
                if file_path.is_file():
                    sdist_zip.write(file_path, file_path.relative_to(plugin_dir))

        # 4. Stage artifacts with ABI-tagged filenames and update manifest
        binaries_dir = staging_dir / "bin"
        binaries_dir.mkdir(exist_ok=True)
        
        # Construct new filename with arch, os, and ABI tag
        base_name = compiled_lib.stem # e.g., "libplugin_a"
        ext = compiled_lib.suffix     # e.g., ".so"
        triplet = host_platform["triplet"]
        abi_signature = host_platform["abi_signature"]
        tagged_filename = f"{base_name}.{triplet}.{abi_signature}{ext}"
        staged_lib_path = binaries_dir / tagged_filename
        
        print(f"    - Staging binary as: {tagged_filename}")
        shutil.copy(compiled_lib, staged_lib_path)

        manifest["bundlePlugins"][plugin_name] = {
            "sdist": {
                "path": sdist_path.name,
                "sdistBundledOn": datetime.datetime.now().isoformat(),
                "buildable": True
            },
            "binaries": [{
                "platform": {
                    "triplet": host_platform["triplet"],
                    "abi_signature": host_platform["abi_signature"]
                },
                "path": staged_lib_path.relative_to(staging_dir).as_posix(),
                "compiledOn": datetime.datetime.now().isoformat()
            }]
        }

    # 5. Write manifest and package final bundle
    manifest_path = staging_dir / "manifest.yaml"
    with open(manifest_path, 'w') as f:
        yaml.dump(manifest, f, sort_keys=False)

    print(f"\nPackaging final bundle: {output_bundle}")
    with zipfile.ZipFile(output_bundle, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
        for root, _, files in os.walk(staging_dir):
            for file in files:
                file_path = Path(root) / file
                bundle_zip.write(file_path, file_path.relative_to(staging_dir))

    shutil.rmtree(staging_dir)
    print("\n✅ Bundle created successfully!")
