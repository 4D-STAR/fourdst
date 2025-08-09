# fourdst/cli/bundle/diff.py
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from fourdst.core.bundle import diff_bundle

console = Console()

def bundle_diff(
    bundle_a_path: Path = typer.Argument(..., help="The first bundle to compare.", exists=True, readable=True),
    bundle_b_path: Path = typer.Argument(..., help="The second bundle to compare.", exists=True, readable=True),
):
    """
    Compares two bundle files, showing differences in their manifests, signatures, and contents.
    """
    console.print(Panel(f"Comparing [bold blue]{bundle_a_path.name}[/bold blue] with [bold blue]{bundle_b_path.name}[/bold blue]"))

    try:
        results = diff_bundle(bundle_a_path, bundle_b_path, progress_callback=typer.echo)
    except Exception as e:
        typer.secho(f"Error comparing bundles: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # --- 1. Display Signature Differences ---
    sig_status = results['signature']['status']
    style_map = {
        'UNCHANGED': ('[green]UNCHANGED[/green]', 'green'),
        'REMOVED': ('[yellow]REMOVED[/yellow]', 'yellow'),
        'ADDED': ('[yellow]ADDED[/yellow]', 'yellow'),
        'CHANGED': ('[bold red]CHANGED[/bold red]', 'red'),
        'UNSIGNED': ('[dim]Both Unsigned[/dim]', 'dim'),
    }
    sig_text, sig_style = style_map.get(sig_status, (sig_status, 'white'))
    console.print(Panel(f"Signature Status: {sig_text}", title="[bold]Signature Verification[/bold]", border_style=sig_style, expand=False))

    # --- 2. Display Manifest Differences ---
    manifest_diff = results['manifest']['diff']
    if manifest_diff:
        diff_text = Text()
        for line in manifest_diff:
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

    # --- 3. Display File Content Differences ---
    file_diffs = results['files']
    if file_diffs:
        table = Table(title="File Content Comparison")
        table.add_column("File Path", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="yellow")

        status_map = {
            'REMOVED': '[red]REMOVED[/red]',
            'ADDED': '[green]ADDED[/green]',
            'MODIFIED': '[yellow]MODIFIED[/yellow]'
        }

        for diff in file_diffs:
            status_text = status_map.get(diff['status'], diff['status'])
            table.add_row(diff['path'], status_text, diff['details'])
        
        console.print(table)
    else:
        console.print(Panel("[green]All file contents are identical.[/green]", title="[bold]File Contents[/bold]", border_style="green"))
