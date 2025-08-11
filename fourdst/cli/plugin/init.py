# fourdst/cli/plugin/init.py

import typer
import sys
from pathlib import Path
import questionary

from fourdst.core.plugin import parse_cpp_interface, generate_plugin_project

plugin_app = typer.Typer()

@plugin_app.command("init")
def plugin_init(
        project_name: str = typer.Argument(..., help="The name of the new plugin project."),
        header: Path = typer.Option(..., "--header", "-H", help="Path to the C++ header file defining the plugin interface.", exists=True, file_okay=True, dir_okay=False, readable=True),
        directory: Path = typer.Option(".", "-d", "--directory", help="The directory to create the project in.", resolve_path=True),
        version: str = typer.Option("0.1.0", "--ver", help="The initial SemVer version of the plugin."),
        libplugin_rev: str = typer.Option("main", "--libplugin-rev", help="The git revision of libplugin to use.")
):
    """
    Initializes a new Meson-based C++ plugin project from an interface header.
    """
    print(f"Parsing interface header: {header.name}")
    
    # Parse the C++ header using core function
    parse_result = parse_cpp_interface(header)
    if not parse_result['success']:
        print(f"Error: {parse_result['error']}", file=sys.stderr)
        raise typer.Exit(code=1)
    
    interfaces = parse_result['data']
    if not interfaces:
        print(f"Error: No suitable interfaces (classes with pure virtual methods) found in {header}", file=sys.stderr)
        raise typer.Exit(code=1)

    # Display found interfaces
    for interface_name, methods in interfaces.items():
        print(f"Found interface: '{interface_name}'")
        for method in methods:
            print(f"  -> Found pure virtual method: {method['signature']}")

    # Interactive Selection
    chosen_interface = questionary.select(
        "Which interface would you like to implement?",
        choices=list(interfaces.keys())
    ).ask()

    if not chosen_interface:
        raise typer.Exit() # User cancelled

    print(f"Initializing plugin '{project_name}' implementing interface '{chosen_interface}'...")

    # Generate the project using core function
    config = {
        'project_name': project_name,
        'header_path': header,
        'directory': directory,
        'version': version,
        'libplugin_rev': libplugin_rev,
        'chosen_interface': chosen_interface,
        'interfaces': interfaces
    }
    
    generation_result = generate_plugin_project(config)
    if not generation_result['success']:
        print(f"Error creating project structure: {generation_result['error']}", file=sys.stderr)
        raise typer.Exit(code=1)

    # Display results
    project_data = generation_result['data']
    for file_path in project_data['files_created']:
        print(f"  -> Created {file_path}")

    print("\n✅ Project initialized successfully and committed to Git!")
    print("To build your new plugin:")
    print(f"  cd {project_data['project_path']}")
    print("  meson setup builddir")
    print("  meson compile -C builddir")
