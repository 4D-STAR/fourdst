# fourdst/cli/plugin/diff.py
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

console = Console()

def _extract_sdist(bundle_path: Path, plugin_name: str, temp_dir: Path):
    """Extracts a specific plugin's sdist from a bundle to a directory."""
    sdist_extract_path = temp_dir / f"{plugin_name}_src"
    
    with tempfile.TemporaryDirectory() as bundle_unpack_dir_str:
        bundle_unpack_dir = Path(bundle_unpack_dir_str)
        
        with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
            bundle_zip.extractall(bundle_unpack_dir)
            
        manifest_path = bundle_unpack_dir / "manifest.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError("manifest.yaml not found in bundle.")
            
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
            
        plugin_data = manifest.get('bundlePlugins', {}).get(plugin_name)
        if not plugin_data or 'sdist' not in plugin_data:
            raise FileNotFoundError(f"Plugin '{plugin_name}' or its sdist not found in {bundle_path.name}.")
            
        sdist_path_in_bundle = bundle_unpack_dir / plugin_data['sdist']['path']
        if not sdist_path_in_bundle.exists():
            raise FileNotFoundError(f"sdist archive '{plugin_data['sdist']['path']}' not found in bundle.")
            
        with zipfile.ZipFile(sdist_path_in_bundle, 'r') as sdist_zip:
            sdist_zip.extractall(sdist_extract_path)
            
    return sdist_extract_path

def plugin_diff(
    plugin_name: str = typer.Argument(..., help="The name of the plugin to compare."),
    bundle_a_path: Path = typer.Argument(..., help="The first bundle to compare.", exists=True, readable=True),
    bundle_b_path: Path = typer.Argument(..., help="The second bundle to compare.", exists=True, readable=True),
):
    """
    Compares the source code of a specific plugin between two different bundles.
    """
    console.print(Panel(f"Comparing source for plugin [bold blue]{plugin_name}[/bold blue] between bundles"))

    with tempfile.TemporaryDirectory() as temp_a_str, tempfile.TemporaryDirectory() as temp_b_str:
        try:
            src_a_path = _extract_sdist(bundle_a_path, plugin_name, Path(temp_a_str))
            src_b_path = _extract_sdist(bundle_b_path, plugin_name, Path(temp_b_str))
        except FileNotFoundError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)

        files_a = {p.relative_to(src_a_path) for p in src_a_path.rglob('*') if p.is_file()}
        files_b = {p.relative_to(src_b_path) for p in src_b_path.rglob('*') if p.is_file()}

        added_files = files_b - files_a
        removed_files = files_a - files_b
        common_files = files_a & files_b
        
        has_changes = False

        if added_files:
            has_changes = True
            console.print(Panel("\n".join(f"[green]+ {f}[/green]" for f in sorted(list(added_files))), title="[bold]Added Files[/bold]"))
        
        if removed_files:
            has_changes = True
            console.print(Panel("\n".join(f"[red]- {f}[/red]" for f in sorted(list(removed_files))), title="[bold]Removed Files[/bold]"))

        modified_files_count = 0
        for file_rel_path in sorted(list(common_files)):
            content_a = (src_a_path / file_rel_path).read_text()
            content_b = (src_b_path / file_rel_path).read_text()

            if content_a != content_b:
                has_changes = True
                modified_files_count += 1
                diff = difflib.unified_diff(
                    content_a.splitlines(keepends=True),
                    content_b.splitlines(keepends=True),
                    fromfile=f"a/{file_rel_path}",
                    tofile=f"b/{file_rel_path}",
                )
                diff_text = Text()
                for line in diff:
                    if line.startswith('+'): diff_text.append(line, style="green")
                    elif line.startswith('-'): diff_text.append(line, style="red")
                    else: diff_text.append(line)
                
                console.print(Panel(diff_text, title=f"[bold yellow]Modified: {file_rel_path}[/bold yellow]", border_style="yellow", expand=False))

        if not has_changes:
            console.print(Panel("[green]No source code changes detected for this plugin.[/green]", title="Result"))
        else:
            console.print(f"\nFound changes in {modified_files_count} file(s).")
