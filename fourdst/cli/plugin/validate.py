# fourdst/cli/plugin/validate.py
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from fourdst.core.plugin import validate_plugin_project

console = Console()

def plugin_validate(
    plugin_path: Path = typer.Argument(
        ".",
        help="The path to the plugin directory to validate.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True
    )
):
    """
    Validates a plugin's structure and meson.build file.
    """
    console.print(Panel(f"Validating Plugin: [bold]{plugin_path.name}[/bold]", border_style="blue"))

    # Validate using core function
    validate_result = validate_plugin_project(plugin_path)
    if not validate_result['success']:
        console.print(f"[red]Error during validation: {validate_result['error']}[/red]")
        raise typer.Exit(code=1)

    # Display results
    validate_data = validate_result['data']
    errors = validate_data['errors']
    warnings = validate_data['warnings']
    checks = validate_data['checks']

    # Display each check result
    for check in checks:
        if check['passed']:
            console.print(Text(f"✅ {check['message']}", style="green"))
        else:
            if check['is_warning']:
                console.print(Text(f"⚠️ {check['message']}", style="yellow"))
            else:
                console.print(Text(f"❌ {check['message']}", style="red"))

    # Final summary
    console.print("-" * 40)
    if not errors:
        console.print(Panel(
            f"[bold green]Validation Passed[/bold green]\nWarnings: {len(warnings)}",
            title="Result",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[bold red]Validation Failed[/bold red]\nErrors: {len(errors)}\nWarnings: {len(warnings)}",
            title="Result",
            border_style="red"
        ))
        raise typer.Exit(code=1)
