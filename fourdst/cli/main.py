# fourdst/cli/main.py

import typer
import os
import sys
import shutil
import subprocess
from pathlib import Path
import importlib.resources
import questionary
from clang import cindex

# --- Main Typer application ---
app = typer.Typer(
    name="fourdst-cli",
    help="A command-line tool for managing fourdst projects and plugins."
)
plugin_app = typer.Typer(name="plugin", help="Commands for managing fourdst plugins.")
app.add_typer(plugin_app, name="plugin")

def get_template_content(template_name: str) -> str:
    """Safely reads content from a template file packaged with the CLI."""
    try:
        return importlib.resources.files('fourdst.cli.templates').joinpath(template_name).read_text()
    except FileNotFoundError:
        print(f"Error: Template file '{template_name}' not found.", file=sys.stderr)
        sys.exit(1)

def parse_cpp_header(header_path: Path):
    """
    Parses a C++ header file using libclang to find classes and their pure virtual methods.
    """
    if not cindex.Config.loaded:
        try:
            cindex.Config.set_library_file(cindex.conf.get_filename())
        except cindex.LibclangError as e:
            print(f"Error: libclang library not found. Please ensure it's installed and in your system's path.", file=sys.stderr)
            print(f"Details: {e}", file=sys.stderr)
            raise typer.Exit(code=1)

    # --- Get compiler flags from pkg-config to help clang find includes ---
    try:
        pkg_config_proc = subprocess.run(
            ['pkg-config', '--cflags', 'fourdst_plugin'],
            capture_output=True,
            text=True,
            check=True
        )
        # Split the flags string into a list of arguments for libclang
        compiler_flags = pkg_config_proc.stdout.strip().split()
        print(f"Using compiler flags from pkg-config: {' '.join(compiler_flags)}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: `pkg-config --cflags fourdst-plugin` failed. Parsing may not succeed if the header has dependencies.", file=sys.stderr)
        print("Please ensure 'pkg-config' is installed and 'fourdst-plugin.pc' is in your PKG_CONFIG_PATH.", file=sys.stderr)
        compiler_flags = []

    index = cindex.Index.create()
    # Add the pkg-config flags to the parser arguments
    translation_unit = index.parse(str(header_path), args=['-x', 'c++', '-std=c++23'] + compiler_flags)

    interfaces = {}
    for cursor in translation_unit.cursor.walk_preorder():
        if cursor.kind == cindex.CursorKind.CLASS_DECL and cursor.is_definition():
            class_name = cursor.spelling
            methods = []
            for child in cursor.get_children():
                if child.kind == cindex.CursorKind.CXX_METHOD and child.is_pure_virtual_method():
                    method_name = child.spelling
                    result_type = child.result_type.spelling
                    # Recreate the full method signature
                    params = [p.spelling or f"param{i+1}" for i, p in enumerate(child.get_arguments())]
                    param_str = ", ".join(f"{p.type.spelling} {p.spelling}" for p in child.get_arguments())
                    const_qualifier = " const" if child.is_const_method() else ""

                    signature = f"{result_type} {method_name}({param_str}){const_qualifier}"

                    # Generate a placeholder body
                    body = f"    // TODO: Implement the {method_name} method.\n"
                    if result_type != "void":
                        body += f"    return {{}};" # Default return

                    methods.append({'signature': signature, 'body': body})

            if methods: # Only consider classes with pure virtual methods as interfaces
                interfaces[class_name] = methods

    return interfaces

@plugin_app.command("init")
def plugin_init(
        project_name: str = typer.Argument(..., help="The name of the new plugin project."),
        header: Path = typer.Option(..., "--header", "-H", help="Path to the C++ header file defining the plugin interface.", exists=True, file_okay=True, dir_okay=False, readable=True),
        directory: Path = typer.Option(".", "-d", "--directory", help="The directory to create the project in.", resolve_path=True),
        version: str = typer.Option("0.1.0", "--ver", help="The initial SemVer version of the plugin.")
):
    """
    Initializes a new Meson-based C++ plugin project from an interface header.
    """
    print(f"Parsing interface header: {header.name}")
    interfaces = parse_cpp_header(header)

    if not interfaces:
        print(f"Error: No suitable interfaces (classes with pure virtual methods) found in {header}", file=sys.stderr)
        raise typer.Exit(code=1)

    # --- Interactive Selection ---
    chosen_interface = questionary.select(
        "Which interface would you like to implement?",
        choices=list(interfaces.keys())
    ).ask()

    if not chosen_interface:
        raise typer.Exit() # User cancelled

    print(f"Initializing plugin '{project_name}' implementing interface '{chosen_interface}'...")

    # --- Code Generation ---
    method_stubs = "\n".join(
        f"    {method['signature']} override {{\n{method['body']}\n    }}"
        for method in interfaces[chosen_interface]
    )

    class_name = ''.join(filter(str.isalnum, project_name.replace('_', ' ').title().replace(' ', ''))) + "Plugin"
    root_path = directory / project_name
    src_path = root_path / "src"
    include_path = root_path / "include"

    try:
        src_path.mkdir(parents=True, exist_ok=True)
        include_path.mkdir(exist_ok=True)

        # --- Create meson.build from template ---
        meson_template = get_template_content("meson.build.in")
        meson_content = meson_template.format(
            project_name=project_name,
            version=version,
            interface_include_dir=header.parent.resolve()
        )
        (root_path / "meson.build").write_text(meson_content)
        print(f"  -> Created {root_path / 'meson.build'}")

        # --- Create C++ source file from template ---
        cpp_template = get_template_content("plugin.cpp.in")
        cpp_content = cpp_template.format(
            class_name=class_name,
            project_name=project_name,
            interface=chosen_interface,
            interface_header_path=header.absolute(),
            method_stubs=method_stubs
        )
        (src_path / f"{project_name}.cpp").write_text(cpp_content)
        print(f"  -> Created {src_path / f'{project_name}.cpp'}")

        # --- Create .gitignore ---
        (root_path / ".gitignore").write_text("builddir/\n")
        print(f"  -> Created {root_path / '.gitignore'}")

    except OSError as e:
        print(f"Error creating project structure: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    print("\nProject initialized successfully!")
    print("To build your new plugin:")
    print(f"  cd {root_path}")
    print("  meson setup builddir")
    print("  meson compile -C builddir")

if __name__ == "__main__":
    app()