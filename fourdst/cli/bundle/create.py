# fourdst/cli/bundle/create.py

import typer
import os
import sys
import shutil
import datetime
import yaml
import zipfile
from pathlib import Path
from fourdst.cli.common.utils import get_platform_identifier, get_macos_targeted_platform_identifier, run_command

bundle_app = typer.Typer()

@bundle_app.command("create")
def bundle_create(
    plugin_dirs: list[Path] = typer.Argument(..., help="A list of plugin project directories to include.", exists=True, file_okay=False),
    output_bundle: Path = typer.Option("bundle.fbundle", "--out", "-o", help="The path for the output bundle file."),
    bundle_name: str = typer.Option("MyPluginBundle", "--name", help="The name of the bundle."),
    bundle_version: str = typer.Option("0.1.0", "--ver", help="The version of the bundle."),
    bundle_author: str = typer.Option("Unknown", "--author", help="The author of the bundle."),
    # --- NEW OPTION ---
    target_macos_version: str = typer.Option(None, "--target-macos-version", help="The minimum macOS version to target (e.g., '12.0').")
):
    """
    Builds and packages one or more plugin projects into a single .fbundle file.
    """
    staging_dir = Path("temp_bundle_staging")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir()

    # --- MODIFIED LOGIC ---
    # Prepare environment for the build
    build_env = os.environ.copy()
    
    # Determine the host platform identifier based on the target
    if sys.platform == "darwin" and target_macos_version:
        typer.secho(f"Targeting macOS version: {target_macos_version}", fg=typer.colors.CYAN)
        host_platform = get_macos_targeted_platform_identifier(target_macos_version)
        
        # Set environment variables for Meson to pick up
        flags = f"-mmacosx-version-min={target_macos_version}"
        build_env["CXXFLAGS"] = f"{build_env.get('CXXFLAGS', '')} {flags}".strip()
        build_env["LDFLAGS"] = f"{build_env.get('LDFLAGS', '')} {flags}".strip()
    else:
        # Default behavior for Linux or non-targeted macOS builds
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

        # 1. Build the plugin using the prepared environment
        print(f"    - Compiling for target platform...")
        build_dir = plugin_dir / "builddir"
        if build_dir.exists():
            shutil.rmtree(build_dir) # Reconfigure every time to apply env vars

        # Pass the modified environment to the Meson commands
        run_command(["meson", "setup", "builddir"], cwd=plugin_dir, env=build_env)
        run_command(["meson", "compile", "-C", "builddir"], cwd=plugin_dir, env=build_env)

        # 2. Find the compiled artifact
        compiled_lib = next(build_dir.glob("lib*.so"), None) or next(build_dir.glob("lib*.dylib"), None)
        if not compiled_lib:
            print(f"Error: Could not find compiled library for {plugin_name} (expected lib*.so or lib*.dylib)", file=sys.stderr)
            raise typer.Exit(code=1)

        # 3. Package source code (sdist), respecting .gitignore
        print("    - Packaging source code (respecting .gitignore)...")
        sdist_path = staging_dir / f"{plugin_name}_src.zip"
        
        git_check = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=plugin_dir, check=False)
        
        files_to_include = []
        if git_check.returncode == 0:
            result = run_command(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=plugin_dir)
            files_to_include = [plugin_dir / f for f in result.stdout.strip().split('\n') if f]
        else:
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
        
        base_name = compiled_lib.stem
        ext = compiled_lib.suffix
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
                    "abi_signature": host_platform["abi_signature"],
                    # Adding arch separately for clarity, matching 'fill' command
                    "arch": host_platform["arch"]
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
