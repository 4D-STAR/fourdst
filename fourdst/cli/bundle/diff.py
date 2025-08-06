# fourdst/cli/bundle/diff.py
import typer
import yaml
import zipfile
from pathlib import Path
import tempfile
import shutil
import difflib
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

console = Console()

def _get_file_content(directory: Path, filename: str):
    file_path = directory / filename
    if not file_path.exists():
        return None
    return file_path.read_bytes()

def bundle_diff(
    bundle_a_path: Path = typer.Argument(..., help="The first bundle to compare.", exists=True, readable=True),
    bundle_b_path: Path = typer.Argument(..., help="The second bundle to compare.", exists=True, readable=True),
):
    """
    Compares two bundle files, showing differences in their manifests, signatures, and contents.
    """
    console.print(Panel(f"Comparing [bold blue]{bundle_a_path.name}[/bold blue] with [bold blue]{bundle_b_path.name}[/bold blue]"))

    with tempfile.TemporaryDirectory() as temp_a_str, tempfile.TemporaryDirectory() as temp_b_str:
        temp_a = Path(temp_a_str)
        temp_b = Path(temp_b_str)

        # Unpack both bundles
        with zipfile.ZipFile(bundle_a_path, 'r') as z: z.extractall(temp_a)
        with zipfile.ZipFile(bundle_b_path, 'r') as z: z.extractall(temp_b)

        # --- 1. Compare Signatures ---
        sig_a = _get_file_content(temp_a, "manifest.sig")
        sig_b = _get_file_content(temp_b, "manifest.sig")
        
        sig_panel_style = "green"
        sig_status = ""
        if sig_a == sig_b and sig_a is not None:
            sig_status = "[green]UNCHANGED[/green]"
        elif sig_a and not sig_b:
            sig_status = "[yellow]REMOVED[/yellow]"
            sig_panel_style = "yellow"
        elif not sig_a and sig_b:
            sig_status = "[yellow]ADDED[/yellow]"
            sig_panel_style = "yellow"
        elif sig_a and sig_b and sig_a != sig_b:
            sig_status = "[bold red]CHANGED[/bold red]"
            sig_panel_style = "red"
        else:
            sig_status = "[dim]Both Unsigned[/dim]"
            sig_panel_style = "dim"
        
        console.print(Panel(f"Signature Status: {sig_status}", title="[bold]Signature Verification[/bold]", border_style=sig_panel_style, expand=False))

        # --- 2. Compare Manifests ---
        manifest_a_content = (temp_a / "manifest.yaml").read_text()
        manifest_b_content = (temp_b / "manifest.yaml").read_text()
        
        if manifest_a_content != manifest_b_content:
            diff = difflib.unified_diff(
                manifest_a_content.splitlines(keepends=True),
                manifest_b_content.splitlines(keepends=True),
                fromfile=f"{bundle_a_path.name}/manifest.yaml",
                tofile=f"{bundle_b_path.name}/manifest.yaml",
            )
            
            diff_text = Text()
            for line in diff:
                if line.startswith('+'):
                    diff_text.append(line, style="green")
                elif line.startswith('-'):
                    diff_text.append(line, style="red")
                elif line.startswith('^'):
                    diff_text.append(line, style="blue")
                else:
                    diff_text.append(line)
            
            console.print(Panel(diff_text, title="[bold]Manifest Differences[/bold]", border_style="yellow"))
        else:
             console.print(Panel("[green]Manifests are identical.[/green]", title="[bold]Manifest[/bold]", border_style="green"))

        # --- 3. Compare File Contents (via checksums) ---
        manifest_a = yaml.safe_load(manifest_a_content)
        manifest_b = yaml.safe_load(manifest_b_content)

        files_a = {p['path']: p.get('checksum') for p in manifest_a.get('bundlePlugins', {}).get(next(iter(manifest_a.get('bundlePlugins', {})), ''), {}).get('binaries', [])}
        files_b = {p['path']: p.get('checksum') for p in manifest_b.get('bundlePlugins', {}).get(next(iter(manifest_b.get('bundlePlugins', {})), ''), {}).get('binaries', [])}

        table = Table(title="File Content Comparison")
        table.add_column("File Path", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="yellow")

        all_files = sorted(list(set(files_a.keys()) | set(files_b.keys())))
        has_content_changes = False

        for file in all_files:
            in_a = file in files_a
            in_b = file in files_b

            if in_a and not in_b:
                table.add_row(file, "[red]REMOVED[/red]", "")
                has_content_changes = True
            elif not in_a and in_b:
                table.add_row(file, "[green]ADDED[/green]", "")
                has_content_changes = True
            elif files_a[file] != files_b[file]:
                table.add_row(file, "[yellow]MODIFIED[/yellow]", f"Checksum changed from {files_a.get(file, 'N/A')} to {files_b.get(file, 'N/A')}")
                has_content_changes = True
        
        if has_content_changes:
            console.print(table)
        else:
            console.print(Panel("[green]All file contents are identical.[/green]", title="[bold]File Contents[/bold]", border_style="green"))
