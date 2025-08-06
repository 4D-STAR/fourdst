# fourdst/cli/plugin/init.py

import typer
import sys
import shutil
from pathlib import Path
import questionary

from fourdst.cli.common.utils import run_command, get_template_content
from fourdst.cli.common.templates import GITIGNORE_CONTENT

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
    include_path = src_path / "include"
    subprojects_path = root_path / "subprojects"
    
    try:
        src_path.mkdir(parents=True, exist_ok=True)
        include_path.mkdir(exist_ok=True)
        subprojects_path.mkdir(exist_ok=True)

        # --- Copy interface header to make project self-contained ---
        local_header_path = include_path / header.name
        shutil.copy(header, local_header_path)
        print(f"  -> Copied interface header to {local_header_path.relative_to(root_path)}")

        # --- Create libplugin.wrap file ---
        libplugin_wrap_content = f"""[wrap-git]
url = https://github.com/4D-STAR/libplugin
revision = {libplugin_rev}
depth = 1
"""
        (subprojects_path / "libplugin.wrap").write_text(libplugin_wrap_content)
        print(f"  -> Created {subprojects_path / 'libplugin.wrap'}")

        # --- Create meson.build from template ---
        meson_template = get_template_content("meson.build.in")
        meson_content = meson_template.format(
            project_name=project_name,
            version=version
        )
        (root_path / "meson.build").write_text(meson_content)
        print(f"  -> Created {root_path / 'meson.build'}")

        # --- Create C++ source file from template ---
        cpp_template = get_template_content("plugin.cpp.in")
        cpp_content = cpp_template.format(
            class_name=class_name,
            project_name=project_name,
            interface=chosen_interface,
            interface_header_path=header.name, # Use just the filename
            method_stubs=method_stubs
        )
        (src_path / f"{project_name}.cpp").write_text(cpp_content)
        print(f"  -> Created {src_path / f'{project_name}.cpp'}")

        # --- Create .gitignore ---
        (root_path / ".gitignore").write_text(GITIGNORE_CONTENT)
        print(f"  -> Created .gitignore")

        # --- Initialize Git Repository ---
        print("  -> Initializing Git repository...")
        run_command(["git", "init"], cwd=root_path)
        run_command(["git", "add", "."], cwd=root_path)
        commit_message = f"Initial commit: Scaffold fourdst plugin '{project_name}'"
        run_command(["git", "commit", "-m", commit_message], cwd=root_path)


    except OSError as e:
        print(f"Error creating project structure: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    print("\n✅ Project initialized successfully and committed to Git!")
    print("To build your new plugin:")
    print(f"  cd {root_path}")
    print("  meson setup builddir")
    print("  meson compile -C builddir")

def parse_cpp_header(header_path: Path):
    """
    Parses a C++ header file using libclang to find classes and their pure virtual methods.
    """
    # This function requires python-clang-16
    try:
        from clang import cindex
    except ImportError:
        print("Error: The 'init' command requires 'libclang'. Please install it.", file=sys.stderr)
        print("Run: pip install python-clang-16", file=sys.stderr)
        # Also ensure the libclang.so/dylib is in your system's library path.
        raise typer.Exit(code=1)
        
    if not cindex.Config.loaded:
        try:
            # Attempt to find libclang automatically. This may need to be configured by the user.
            cindex.Config.set_library_file(cindex.conf.get_filename())
        except cindex.LibclangError as e:
            print(f"Error: libclang library not found. Please ensure it's installed and in your system's path.", file=sys.stderr)
            print(f"Details: {e}", file=sys.stderr)
            raise typer.Exit(code=1)

    index = cindex.Index.create()
    translation_unit = index.parse(str(header_path))

    interfaces = {}

    for node in translation_unit.cursor.get_children():
        if node.kind == cindex.CursorKind.CLASS_DECL and node.is_pure_virtual():
            # Found a class with pure virtual methods, likely an interface
            interface_name = node.spelling
            print(f"Found interface: {interface_name}")

            methods = []
            for method in node.get_children():
                if method.kind == cindex.CursorKind.CXX_METHOD and method.is_pure_virtual():
                    # Only consider pure virtual methods
                    method_signature = f"{method.return_type.spelling} {method.spelling}({', '.join([arg.type.spelling for arg in method.get_arguments()])})"
                    method_body = "// TODO: Implement this method"
                    methods.append({"signature": method_signature, "body": method_body})
                    print(f"  Found pure virtual method: {method_signature}")

            interfaces[interface_name] = methods

    return interfaces
