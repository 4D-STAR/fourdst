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
from rich.table import Table

console = Console()

def _calculate_sha256(file_path: Path) -> str:
    """Calculates the SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def _validate_bundle_directory(path: Path, is_temp: bool = False, display_name: str = None):
    """Validates a directory that is structured like an unpacked bundle."""
    title = "Validating Pre-Bundle Directory" if not is_temp else "Validating Bundle Contents"
    name = display_name or path.name
    console.print(Panel(f"{title}: [bold]{name}[/bold]", border_style="blue"))

    errors = 0
    warnings = 0

    # Section 1: Manifest file check
    console.print(Panel("1. Manifest File Check", border_style="cyan"))

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
    console.print(Panel("2. Manifest Content Validation", border_style="cyan"))
    check(manifest is not None, "Manifest is not empty.", "Manifest file is empty.", is_warning=True)
    check('bundleName' in manifest, "Manifest contains 'bundleName'.", "Manifest is missing 'bundleName'.")
    check('bundleVersion' in manifest, "Manifest contains 'bundleVersion'.", "Manifest is missing 'bundleVersion'.")
    
    plugins = manifest.get('bundlePlugins', {})
    check(plugins, "Manifest contains 'bundlePlugins' section.", "Manifest is missing 'bundlePlugins' section.")

    # Build Manifest Validation table
    manifest_table = Table(title="Manifest Validation")
    manifest_table.add_column("Check")
    manifest_table.add_column("Status")
    manifest_table.add_row("manifest.yaml exists", "✅" if manifest_file.is_file() else "❌")
    # YAML parse status already captured by exception above
    manifest_table.add_row("Manifest parses as YAML", "✅")
    manifest_table.add_row("Manifest not empty", "✅" if manifest is not None else "⚠️")
    manifest_table.add_row("bundleName present", "✅" if 'bundleName' in manifest else "❌")
    manifest_table.add_row("bundleVersion present", "✅" if 'bundleVersion' in manifest else "❌")
    has_plugins = bool(manifest.get('bundlePlugins'))
    manifest_table.add_row("bundlePlugins section", "✅" if has_plugins else "❌")
    console.print(manifest_table)
    plugins = manifest.get('bundlePlugins', {})

    # 3. Check files listed in manifest
    console.print(Panel("3. Plugin Validation", border_style="magenta"))
    for name, data in plugins.items():
        console.print(Panel(f"Plugin: [bold cyan]{name}[/bold cyan]", border_style="magenta"))
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
    
    # Build Plugin Validation table
    plugin_table = Table(title="Plugin Validation")
    plugin_table.add_column("Plugin")
    plugin_table.add_column("Sdist Defined")
    plugin_table.add_column("Sdist Exists")
    plugin_table.add_column("Binaries OK")
    plugin_table.add_column("Checksums OK")
    for name, data in plugins.items():
        # sdist checks
        sdist_path_str = data.get('sdist', {}).get('path')
        sdist_defined = bool(sdist_path_str)
        sdist_exists = sdist_defined and (path/ sdist_path_str).exists()
        # binary & checksum checks
        binaries = data.get('binaries', [])
        binaries_ok = all(b.get('path') and (path/ b['path']).exists() for b in binaries)
        checksums_ok = all(('checksum' in b and ("sha256:"+_calculate_sha256(path/ b['path']))==b['checksum']) for b in binaries)
        plugin_table.add_row(
            name,
            "✅" if sdist_defined else "❌",
            "✅" if sdist_exists else "❌",
            "✅" if binaries_ok else "❌",
            "✅" if checksums_ok else "❌"
        )
    console.print(plugin_table)

    # 4. Check for signature
    console.print(Panel("4. Signature Check", border_style="yellow"))
    check((path / "manifest.sig").exists(), "Signature file 'manifest.sig' found.", "Signature file 'manifest.sig' is missing.", is_warning=True)

    # Build Signature Check table
    sig_table = Table(title="Signature Validation")
    sig_table.add_column("Item")
    sig_table.add_column("Status")
    sig_exists = (path / "manifest.sig").exists()
    sig_table.add_row(
        "manifest.sig",
        "✅" if sig_exists else "⚠️"
    )
    console.print(sig_table)

    # Final summary
    console.print("-" * 40)
    # Display summary in a table

    summary_table = Table(title="Validation Summary")
    summary_table.add_column("Result")
    summary_table.add_column("Errors", justify="right")
    summary_table.add_column("Warnings", justify="right")

    if errors == 0:
        result = "Passed"
        style = "green"
    else:
        result = "Failed"
        style = "red"

    summary_table.add_row(
        f"[bold {style}]{result}[/bold {style}]",
        str(errors),
        str(warnings)
    )
    console.print(summary_table)
    if errors != 0:
        raise typer.Exit(code=1)

def _validate_bundle_file(bundle_path: Path):
    """Unpacks a .fbundle file and runs directory validation on its contents."""
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        try:
            with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
                bundle_zip.extractall(temp_dir)
            _validate_bundle_directory(temp_dir, is_temp=True, display_name=bundle_path.name)
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
