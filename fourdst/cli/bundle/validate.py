# fourdst/cli/bundle/validate.py
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from fourdst.core.bundle import validate_bundle

console = Console()

def bundle_validate(
    bundle_path: Path = typer.Argument(
        ...,
        help="The .fbundle file to validate.",
        exists=True,
        resolve_path=True,
        file_okay=True,
        dir_okay=False
    )
):
    """
    Validates the integrity and checksums of a .fbundle file.
    """
    def progress_callback(message):
        # For a CLI, we can choose to show progress or just wait for the final report.
        # In this case, the final report is more structured and useful.
        pass

    try:
        results = validate_bundle(
            bundle_path=bundle_path,
            progress_callback=progress_callback
        )

        console.print(Panel(f"Validation Report for: [bold]{bundle_path.name}[/bold]", border_style="blue"))

        if results['errors']:
            console.print(Panel("Errors", border_style="red", expand=False))
            for error in results['errors']:
                console.print(Text(f"❌ {error}", style="red"))

        if results['warnings']:
            console.print(Panel("Warnings", border_style="yellow", expand=False))
            for warning in results['warnings']:
                console.print(Text(f"⚠️ {warning}", style="yellow"))

        # Summary Table
        summary_table = Table(title="Validation Summary")
        summary_table.add_column("Result")
        summary_table.add_column("Errors", justify="right")
        summary_table.add_column("Warnings", justify="right")

        status = results.get('status', 'failed')
        summary = results.get('summary', {'errors': len(results['errors']), 'warnings': len(results['warnings'])})

        if status == 'passed':
            result_text = "Passed"
            style = "green"
        else:
            result_text = "Failed"
            style = "red"

        summary_table.add_row(
            f"[bold {style}]{result_text}[/bold {style}]",
            str(summary['errors']),
            str(summary['warnings'])
        )
        console.print(summary_table)

        if status != 'passed':
            raise typer.Exit(code=1)
        else:
            console.print("\n[bold green]✅ Bundle is valid.[/bold green]")

    except Exception as e:
        # Catch exceptions from the core function itself
        console.print(Panel(f"[bold red]An unexpected error occurred:[/bold red]\n{e}", title="Validation Error"))
        raise typer.Exit(code=1)
