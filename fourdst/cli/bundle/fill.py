# fourdst/cli/bundle/fill.py

import typer
import shutil
import datetime
import yaml
import zipfile
from pathlib import Path
import questionary
from prompt_toolkit.key_binding import KeyBindings
from questionary.prompts.checkbox import checkbox
import subprocess
import sys
import traceback

try:
    import docker
except ImportError:
    docker = None # Docker is an optional dependency for the 'fill' command

from rich.console import Console
from rich.panel import Panel

console = Console()

from fourdst.core.bundle import get_fillable_targets, fill_bundle
from fourdst.cli.common.utils import run_command_rich # Keep for progress display if needed

custom_key_bindings = KeyBindings()

def _is_arch(target_info, arch_keywords):
    """Helper to check if a target's info contains architecture keywords."""
    # Combine all relevant string values from the target dict to check against.
    text_to_check = ""
    if 'triplet' in target_info:
        text_to_check += target_info['triplet'].lower()
    if 'docker_image' in target_info:
        text_to_check += target_info['docker_image'].lower()
    if 'cross_file' in target_info:
        # Convert path to string for searching
        text_to_check += str(target_info['cross_file']).lower()

    if not text_to_check:
        return False

    return any(keyword in text_to_check for keyword in arch_keywords)

@custom_key_bindings.add('c-a')
def _(event):
    """
    Handler for Ctrl+A. Selects all ARM targets.
    """
    control = event.app.layout.current_control
    # Keywords to identify ARM architectures
    arm_keywords = ['aarch64', 'arm64']

    for i, choice in enumerate(control.choices):
        # The choice.value is the dictionary we passed to questionary.Choice
        target_info = choice.value.get('target', {})
        if _is_arch(target_info, arm_keywords):
            # Add the index to the set of selected items
            if i not in control.selected_indexes:
                control.selected_indexes.add(i)

    # Redraw the UI to show the new selections
    event.app.invalidate()


@custom_key_bindings.add('c-x')
def _(event):
    """
    Handler for Ctrl+X. Selects all x86 targets.
    """
    control = event.app.layout.current_control
    # Keywords to identify x86 architectures
    x86_keywords = ['x86_64', 'x86', 'amd64'] # 'amd64' is a common alias in Docker

    for i, choice in enumerate(control.choices):
        target_info = choice.value.get('target', {})
        if _is_arch(target_info, x86_keywords):
            if i not in control.selected_indexes:
                control.selected_indexes.add(i)

    event.app.invalidate()    

def bundle_fill(bundle_path: Path = typer.Argument(..., help="The .fbundle file to fill with new binaries.", exists=True)):
    """
    Builds new binaries for the current host or cross-targets from the bundle's source.
    """
    staging_dir = Path(f"temp_fill_{bundle_path.stem}")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    
    console.print(Panel(f"[bold]Filling Bundle:[/bold] {bundle_path.name}", expand=False, border_style="blue"))

    # 1. Find available targets and missing binaries using the core function
    try:
        response = get_fillable_targets(bundle_path)
        if not response.get('success', False):
            console.print(f"[red]Error analyzing bundle: {response.get('error', 'Unknown error')}[/red]")
            raise typer.Exit(code=1)
        
        fillable_targets = response.get('data', {})
    except Exception as e:
        console.print(f"[red]Error analyzing bundle: {e}[/red]")
        raise typer.Exit(code=1)

    if not fillable_targets:
        console.print("[green]✅ Bundle is already full for all available build targets.[/green]")
        raise typer.Exit()

    # 2. Create interactive choices for the user
    build_options = []
    BOLD = "\033[1m"
    RESET = "\033[0m"
    CYAN = "\033[36m"
    for plugin_name, targets in fillable_targets.items():
        for target in targets:
            if target['type'] == 'docker':
                display_name = f"Docker: {target['docker_image']}"
            elif target['type'] == 'cross':
                display_name = f"Cross-compile: {Path(target['cross_file']).name}"
            else: # native
                display_name = f"Native: {target['triplet']}"
            
            build_options.append({
                "name": f"Build {plugin_name} for {display_name}",
                "value": {"plugin_name": plugin_name, "target": target}
            })
        
    # 3. Prompt user to select which targets to build
    if not build_options:
        console.print("[yellow]No buildable targets found.[/yellow]")
        raise typer.Exit()

    choices = [
        questionary.Choice(title=opt['name'], value=opt['value'])
        for opt in build_options
    ]

    message = (
        "Select which missing binaries to build:\n"
        "  (Press [Ctrl+A] to select all ARM, [Ctrl+X] to select all x86)"
    )

    # --- START OF FIX ---
    # 1. Instantiate the Checkbox class directly instead of using the shortcut.
    prompt = checkbox(
        message,
        choices=choices,
        # key_bindings=custom_key_bindings
    )

    # 2. Use .unsafe_ask() to run the prompt object.
    selected_jobs = prompt.unsafe_ask()
    # --- END OF FIX ---
    
    if not selected_jobs:
        console.print("No binaries selected to build. Exiting.")
        raise typer.Exit()

    targets_to_build = {}
    for job in selected_jobs:
        plugin_name = job['plugin_name']
        target = job['target']
        if plugin_name not in targets_to_build:
            targets_to_build[plugin_name] = []
        targets_to_build[plugin_name].append(target)

    try:
        console.print("--- Starting build process ---")
        fill_bundle(
            bundle_path,
            targets_to_build,
            progress_callback=lambda msg: console.print(f"[dim]  {msg}[/dim]")
        )
        console.print("--- Build process finished ---")
        console.print(f"[green]✅ Bundle '{bundle_path.name}' has been filled successfully.[/green]")
        console.print("[yellow]⚠️ If the bundle was signed, the signature is now invalid. Please re-sign.[/yellow]")

    except Exception as e:
        console.print(f"[red]An error occurred during the build process: {e}[/red]")
        tb_str = traceback.format_exc()
        console.print(Panel(
            tb_str,
            title="Traceback",
            border_style="red",
            expand=False
        ))
        raise typer.Exit(code=1)
