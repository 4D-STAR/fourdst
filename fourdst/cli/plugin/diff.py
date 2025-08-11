# fourdst/cli/plugin/diff.py
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from fourdst.core.plugin import compare_plugin_sources

console = Console()

def plugin_diff(
    plugin_name: str = typer.Argument(..., help="The name of the plugin to compare."),
    bundle_a_path: Path = typer.Argument(..., help="The first bundle to compare.", exists=True, readable=True),
    bundle_b_path: Path = typer.Argument(..., help="The second bundle to compare.", exists=True, readable=True),
):
    """
    Compares the source code of a specific plugin between two different bundles.
    """
    console.print(Panel(f"Comparing source for plugin [bold blue]{plugin_name}[/bold blue] between bundles"))

    # Compare using core function
    compare_result = compare_plugin_sources(bundle_a_path, bundle_b_path, plugin_name)
    if not compare_result['success']:
        console.print(f"[red]Error: {compare_result['error']}[/red]")
        raise typer.Exit(code=1)

    # Display results
    compare_data = compare_result['data']
    has_changes = compare_data['has_changes']
    added_files = compare_data['added_files']
    removed_files = compare_data['removed_files']
    modified_files = compare_data['modified_files']

    if added_files:
        console.print(Panel("\n".join(f"[green]+ {f}[/green]" for f in added_files), title="[bold]Added Files[/bold]"))
    
    if removed_files:
        console.print(Panel("\n".join(f"[red]- {f}[/red]" for f in removed_files), title="[bold]Removed Files[/bold]"))

    for modified_file in modified_files:
        file_path = modified_file['file_path']
        diff_content = modified_file['diff']
        
        diff_text = Text()
        for line in diff_content.splitlines(keepends=True):
            if line.startswith('+'): 
                diff_text.append(line, style="green")
            elif line.startswith('-'): 
                diff_text.append(line, style="red")
            else: 
                diff_text.append(line)
        
        console.print(Panel(diff_text, title=f"[bold yellow]Modified: {file_path}[/bold yellow]", border_style="yellow", expand=False))

    if not has_changes:
        console.print(Panel("[green]No source code changes detected for this plugin.[/green]", title="Result"))
    else:
        console.print(f"\nFound changes in {len(modified_files)} file(s).")
