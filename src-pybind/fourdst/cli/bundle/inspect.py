# fourdst/cli/bundle/inspect.py

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from fourdst.core.bundle import inspect_bundle

console = Console()

def display_inspection_report(report: dict):
    """
    Displays the inspection report using rich components.
    """
    manifest = report.get('manifest', {})
    host_info = report.get('host_info', {})
    validation = report.get('validation', {})
    signature = report.get('signature', {})
    plugins = report.get('plugins', {})

    # --- Header ---
    console.print(Panel(f"Inspection Report for [bold blue]{manifest.get('bundleName', 'N/A')}[/bold blue]", expand=False))
    
    meta_table = Table.grid(padding=(0, 2))
    meta_table.add_column()
    meta_table.add_column()
    meta_table.add_row("Name:", manifest.get('bundleName', 'N/A'))
    meta_table.add_row("Version:", manifest.get('bundleVersion', 'N/A'))
    meta_table.add_row("Author:", manifest.get('bundleAuthor', 'N/A'))
    meta_table.add_row("Bundled On:", manifest.get('bundledOn', 'N/A'))
    meta_table.add_row("Host ABI:", Text(host_info.get('abi_signature', 'N/A'), style="dim"))
    meta_table.add_row("Host Arch:", Text(host_info.get('triplet', 'N/A'), style="dim"))
    console.print(meta_table)
    console.print("─" * 50)

    # --- Trust Status ---
    status = signature.get('status', 'UNKNOWN')
    if status == 'TRUSTED':
        console.print(Panel(f"[bold green]✅ Trust Status: SIGNED and TRUSTED[/bold green]\nKey: [dim]{signature.get('key_path')}[/dim]", expand=False, border_style="green"))
    elif status == 'UNSIGNED':
        console.print(Panel("[bold yellow]🟡 Trust Status: UNSIGNED[/bold yellow]", expand=False, border_style="yellow"))
    elif status == 'UNTRUSTED':
        console.print(Panel(f"[bold yellow]⚠️ Trust Status: SIGNED but UNTRUSTED AUTHOR[/bold yellow]\nFingerprint: [dim]{signature.get('fingerprint')}[/dim]", expand=False, border_style="yellow"))
    elif status == 'INVALID':
        console.print(Panel(f"[bold red]❌ Trust Status: INVALID SIGNATURE[/bold red]\n{signature.get('reason')}", expand=False, border_style="red"))
    elif status == 'TAMPERED':
        console.print(Panel(f"[bold red]❌ Trust Status: TAMPERED[/bold red]\n{signature.get('reason')}", expand=False, border_style="red"))
    elif status == 'UNSUPPORTED':
        console.print(Panel(f"[bold red]❌ Trust Status: CRYPTOGRAPHY NOT SUPPORTED[/bold red]\n{signature.get('reason')}", expand=False, border_style="red"))
    else:
        console.print(Panel(f"[bold red]❌ Trust Status: ERROR[/bold red]\n{signature.get('reason')}", expand=False, border_style="red"))

    # --- Validation Issues ---
    errors = validation.get('errors', [])
    warnings = validation.get('warnings', [])
    if errors or warnings:
        console.print("─" * 50)
        console.print("[bold]Validation Issues:[/bold]")
        for error in errors:
            console.print(Text(f"  - [red]Error:[/red] {error}"))
        for warning in warnings:
            console.print(Text(f"  - [yellow]Warning:[/yellow] {warning}"))

    # --- Plugin Details ---
    console.print("─" * 50)
    console.print("[bold]Available Plugins:[/bold]")
    if not plugins:
        console.print("  No plugins found in bundle.")

    for name, data in plugins.items():
        console.print(Panel(f"Plugin: [bold]{name}[/bold]", expand=False, border_style="blue"))
        console.print(f"  Source Dist: [dim]{data.get('sdist_path', 'N/A')}[/dim]")
        
        binaries = data.get('binaries', [])
        if not binaries:
            console.print("  Binaries: None")
        else:
            bin_table = Table(title="Binaries", show_header=True, header_style="bold magenta")
            bin_table.add_column("Path")
            bin_table.add_column("Architecture")
            bin_table.add_column("ABI")
            bin_table.add_column("Host Compatible?", style="cyan")
            bin_table.add_column("Reason for Incompatibility", style="red")

            for b in binaries:
                plat = b.get('platform', {})
                style = "green" if b.get('is_compatible') else "default"
                compat_text = "✅ Yes" if b.get('is_compatible') else "No"
                reason = b.get('incompatibility_reason', '') or ''
                bin_table.add_row(
                    Text(b.get('path', 'N/A'), style=style),
                    Text(plat.get('triplet', 'N/A'), style=style),
                    Text(plat.get('abi_signature', 'N/A'), style=style),
                    Text(compat_text, style="cyan"),
                    Text(reason, style="red")
                )
            console.print(bin_table)

        if not data.get('compatible_found'):
            console.print(Text("  Note: No compatible binary found for the current system.", style="yellow"))
            console.print(Text("  Run 'fourdst bundle fill' to build one.", style="yellow"))

def bundle_inspect(bundle_path: Path = typer.Argument(..., help="The .fbundle file to inspect.", exists=True, resolve_path=True)):
    """
    Inspects a bundle, validating its contents and cryptographic signature.
    """
    try:
        report = inspect_bundle(bundle_path)
        display_inspection_report(report)
        # Exit with an error code if validation failed, to support scripting
        if report.get('validation', {}).get('status') != 'passed':
            raise typer.Exit(code=1)
    except Exception:
        console.print_exception(show_locals=True)
        raise typer.Exit(code=1)

