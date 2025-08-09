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
            # On systems like macOS, you might need to point to the specific version, e.g.:
            # cindex.Config.set_library_path('/opt/homebrew/opt/llvm/lib')
            cindex.Config.set_library_file(cindex.conf.get_filename())
        except cindex.LibclangError as e:
            print(f"Error: libclang library not found. Please ensure it's installed and in your system's path.", file=sys.stderr)
            print(f"Details: {e}", file=sys.stderr)
            raise typer.Exit(code=1)

    index = cindex.Index.create()
    # Pass standard C++ arguments to the parser. This improves reliability.
    args = ['-x', 'c++', '-std=c++17']
    translation_unit = index.parse(str(header_path), args=args)

    if not translation_unit:
        print(f"Error: Unable to parse the translation unit {header_path}", file=sys.stderr)
        raise typer.Exit(code=1)

    interfaces = {}

    # --- Recursive function to walk the AST ---
    def walk_ast(node):
        # We are looking for class definitions, not just declarations.
        if node.kind == cindex.CursorKind.CLASS_DECL and node.is_definition():
            # Collect pure virtual methods within this class
            pv_methods = [m for m in node.get_children()
                          if m.kind == cindex.CursorKind.CXX_METHOD and m.is_pure_virtual_method()]
            
            # If it has pure virtual methods, it's an interface we care about
            if pv_methods:
                interface_name = node.spelling
                methods = []
                print(f"Found interface: '{interface_name}'")
                for method in pv_methods:
                    # Get the string representation of all argument types
                    args_str = ', '.join([arg.type.spelling for arg in method.get_arguments()])
                    
                    # Reconstruct the signature from its parts. This is much more reliable.
                    sig = f"{method.result_type.spelling} {method.spelling}({args_str})"
                    
                    # Append 'const' if the method is a const method
                    if method.is_const_method():
                         sig += " const"

                    methods.append({"signature": sig, "body": "      // TODO: Implement this method"})
                    print(f"  -> Found pure virtual method: {sig}")
                
                interfaces[interface_name] = methods
                 
                interfaces[interface_name] = methods

        # --- The recursive step ---
        # Recurse for children of this node
        for child in node.get_children():
            walk_ast(child)

    # Start the traversal from the root of the AST
    walk_ast(translation_unit.cursor)
    
    return interfaces