# fourdst/cli/common/utils.py

import typer
import os
import sys
import subprocess
from pathlib import Path
import importlib.resources

from rich.console import Console
from rich.panel import Panel

console = Console()

def run_command_rich(command: list[str], cwd: Path = None, check=True, env: dict = None):
    """
    Runs a command and displays its output live using rich.
    """
    command_str = ' '.join(command)
    console.print(Panel(f"Running: [bold cyan]{command_str}[/bold cyan]", title="Command", border_style="blue"))

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=env,
        bufsize=1, # line-buffered
        universal_newlines=True
    )

    # Read and print stdout and stderr line by line
    if process.stdout:
        for line in iter(process.stdout.readline, ''):
            console.print(line.strip())
    
    if process.stderr:
        for line in iter(process.stderr.readline, ''):
            console.print(f"[yellow]{line.strip()}[/yellow]")

    process.wait()

    if check and process.returncode != 0:
        console.print(Panel(f"Command failed with exit code {process.returncode}", title="[bold red]Error[/bold red]", border_style="red"))
        raise subprocess.CalledProcessError(process.returncode, command)

    return process

def get_template_content(template_name: str) -> str:
    """Safely reads content from a template file packaged with the CLI."""
    try:
        return importlib.resources.files('fourdst.cli.templates').joinpath(template_name).read_text()
    except FileNotFoundError:
        print(f"Error: Template file '{template_name}' not found.", file=sys.stderr)
        sys.exit(1)

def run_command(command: list[str], cwd: Path = None, check=True, display_output: bool = False, env: dict = None):
    """Runs a command, optionally displaying its output and using a custom environment."""
    command_str = ' '.join(command)
    
    try:
        result = subprocess.run(command, check=check, capture_output=True, text=True, cwd=cwd, env=env)
        
        if display_output and (result.stdout or result.stderr):
            output_text = ""
            if result.stdout:
                output_text += result.stdout.strip()
            if result.stderr:
                output_text += f"\n[yellow]{result.stderr.strip()}[/yellow]"

            console.print(Panel(
                output_text, 
                title=f"Output from: `{command_str}`", 
                border_style="blue",
                expand=False
            ))

        return result
    except subprocess.CalledProcessError as e:
        if check:
            output_text = ""
            if e.stdout:
                output_text += f"[bold]--- STDOUT ---[/bold]\n{e.stdout.strip()}"
            if e.stderr:
                output_text += f"\n[bold]--- STDERR ---[/bold]\n{e.stderr.strip()}"

            console.print(Panel(
                output_text,
                title=f"Error running: `{command_str}`",
                border_style="red",
                expand=False
            ))
            raise typer.Exit(code=1)
        return e

def is_abi_compatible(host_abi: str, binary_abi: str) -> bool:
    """
    Checks if a binary's ABI is compatible with the host's ABI.

    Compatibility is defined as:
    1. Same compiler, stdlib, and ABI name.
    2. Host's stdlib version is >= binary's stdlib version.
    """
    try:
        host_parts = host_abi.split('-')
        bin_parts = binary_abi.split('-')

        if len(host_parts) != 4 or len(bin_parts) != 4:
            # Fallback to exact match for non-standard ABI strings
            return host_abi == binary_abi

        host_compiler, host_stdlib, host_version, host_abi_name = host_parts
        bin_compiler, bin_stdlib, bin_version, bin_abi_name = bin_parts

        # 1. Check for exact match on compiler, stdlib, and abi name
        if not (host_compiler == bin_compiler and host_stdlib == bin_stdlib and host_abi_name == bin_abi_name):
            return False

        # 2. Compare stdlib versions (e.g., "2.41" vs "2.28")
        # We can treat them as dot-separated integers for comparison.
        host_v_parts = list(map(int, host_version.split('.')))
        bin_v_parts = list(map(int, bin_version.split('.')))

        # Pad shorter version with zeros for safe comparison
        max_len = max(len(host_v_parts), len(bin_v_parts))
        host_v_parts.extend([0] * (max_len - len(host_v_parts)))
        bin_v_parts.extend([0] * (max_len - len(bin_v_parts)))

        return host_v_parts >= bin_v_parts

    except (ValueError, IndexError):
        # If parsing fails, fall back to a simple string comparison
        return host_abi == binary_abi

def calculate_sha256(file_path: Path) -> str:
    """Calculates the SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

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
