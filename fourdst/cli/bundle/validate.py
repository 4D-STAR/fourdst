# fourdst/cli/bundle/validate.py
import typer
import yaml
import zipfile
from pathlib import Path
import tempfile
import shutil
import hashlib
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

def _calculate_sha256(file_path: Path) -> str:
    """Calculates the SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def _validate_bundle_directory(path: Path, is_temp: bool = False):
    """Validates a directory that is structured like an unpacked bundle."""
    title = "Validating Pre-Bundle Directory" if not is_temp else "Validating Bundle Contents"
    console.print(Panel(f"{title}: [bold]{path.name}[/bold]", border_style="blue"))
    
    errors = 0
    warnings = 0

    def check(condition, success_msg, error_msg, is_warning=False):
        nonlocal errors, warnings
        if condition:
            console.print(Text(f"✅ {success_msg}", style="green"))
            return True
        else:
            if is_warning:
                console.print(Text(f"⚠️ {error_msg}", style="yellow"))
                warnings += 1
            else:
                console.print(Text(f"❌ {error_msg}", style="red"))
                errors += 1
            return False

    # 1. Check for manifest
    manifest_file = path / "manifest.yaml"
    if not check(manifest_file.is_file(), "Found manifest.yaml.", "Missing manifest.yaml file."):
        raise typer.Exit(code=1)

    try:
        manifest = yaml.safe_load(manifest_file.read_text())
        check(True, "Manifest file is valid YAML.", "")
    except yaml.YAMLError as e:
        check(False, "", f"Manifest file is not valid YAML: {e}")
        raise typer.Exit(code=1)

    # 2. Check manifest content
    check(manifest is not None, "Manifest is not empty.", "Manifest file is empty.", is_warning=True)
    check('bundleName' in manifest, "Manifest contains 'bundleName'.", "Manifest is missing 'bundleName'.")
    check('bundleVersion' in manifest, "Manifest contains 'bundleVersion'.", "Manifest is missing 'bundleVersion'.")
    
    plugins = manifest.get('bundlePlugins', {})
    check(plugins, "Manifest contains 'bundlePlugins' section.", "Manifest is missing 'bundlePlugins' section.")

    # 3. Check files listed in manifest
    for name, data in plugins.items():
        console.print(f"\n--- Validating plugin: [bold cyan]{name}[/bold cyan] ---")
        sdist_info = data.get('sdist', {})
        sdist_path_str = sdist_info.get('path')
        
        if check(sdist_path_str, "sdist path is defined.", f"sdist path not defined for plugin '{name}'."):
            sdist_path = path / sdist_path_str
            check(sdist_path.exists(), f"sdist file found: {sdist_path_str}", f"sdist file not found: {sdist_path_str}")

        for binary in data.get('binaries', []):
            bin_path_str = binary.get('path')
            if not check(bin_path_str, "Binary path is defined.", "Binary entry is missing a 'path'."):
                continue

            bin_path = path / bin_path_str
            if check(bin_path.exists(), f"Binary file found: {bin_path_str}", f"Binary file not found: {bin_path_str}"):
                expected_checksum = binary.get('checksum')
                if check(expected_checksum, "Checksum is defined.", f"Checksum not defined for binary '{bin_path_str}'.", is_warning=True):
                    actual_checksum = "sha256:" + _calculate_sha256(bin_path)
                    check(
                        actual_checksum == expected_checksum,
                        f"Checksum matches for {bin_path_str}",
                        f"Checksum mismatch for {bin_path_str}.\n  Expected: {expected_checksum}\n  Actual:   {actual_checksum}"
                    )
    
    # 4. Check for signature
    check((path / "manifest.sig").exists(), "Signature file 'manifest.sig' found.", "Signature file 'manifest.sig' is missing.", is_warning=True)

    # Final summary
    console.print("-" * 40)
    if errors == 0:
        console.print(Panel(
            f"[bold green]Validation Passed[/bold green]\nWarnings: {warnings}",
            title="Result",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[bold red]Validation Failed[/bold red]\nErrors: {errors}\nWarnings: {warnings}",
            title="Result",
            border_style="red"
        ))
        raise typer.Exit(code=1)

def _validate_bundle_file(bundle_path: Path):
    """Unpacks a .fbundle file and runs directory validation on its contents."""
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        try:
            with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
                bundle_zip.extractall(temp_dir)
            _validate_bundle_directory(temp_dir, is_temp=True)
        except zipfile.BadZipFile:
            console.print(Panel(f"[red]Error: '{bundle_path.name}' is not a valid zip file.[/red]", title="Validation Error"))
            raise typer.Exit(code=1)

def bundle_validate(
    path: Path = typer.Argument(
        ".",
        help="The path to the .fbundle file or pre-bundle directory to validate.",
        exists=True,
        resolve_path=True
    )
):
    """
    Validates a packed .fbundle or a directory ready to be packed.
    
    - If a directory is provided, it checks for a valid manifest and that all referenced files exist.
    - If a .fbundle file is provided, it unpacks it and runs the same validation checks.
    """
    if path.is_dir():
        _validate_bundle_directory(path)
    elif path.is_file():
        _validate_bundle_file(path)
    else:
        # This case should not be reached due to `exists=True`
        console.print(Panel("[red]Error: Path is not a file or directory.[/red]", title="Validation Error"))
        raise typer.Exit(code=1)
