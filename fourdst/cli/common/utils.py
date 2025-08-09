# fourdst/cli/common/utils.py

import typer
import os
import sys
import shutil
import subprocess
from pathlib import Path
import importlib.resources
import json
import platform
import zipfile
import hashlib

try:
    import docker
except ImportError:
    docker = None

from rich.console import Console
from rich.panel import Panel

console = Console()

from fourdst.cli.common.config import CACHE_PATH, ABI_CACHE_FILE, CROSS_FILES_PATH, DOCKER_BUILD_IMAGES
from fourdst.cli.common.templates import ABI_DETECTOR_CPP_SRC, ABI_DETECTOR_MESON_SRC

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
        # Pass the env dictionary to subprocess.run
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

def _detect_and_cache_abi():
    """
    Compiles and runs a C++ program to detect the compiler ABI, then caches it.
    """
    print("Performing one-time native C++ ABI detection...")
    temp_dir = CACHE_PATH / "abi_detector"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    try:
        (temp_dir / "main.cpp").write_text(ABI_DETECTOR_CPP_SRC)
        (temp_dir / "meson.build").write_text(ABI_DETECTOR_MESON_SRC)

        print("  - Configuring detector...")
        run_command(["meson", "setup", "build"], cwd=temp_dir, display_output=True)
        print("  - Compiling detector...")
        run_command(["meson", "compile", "-C", "build"], cwd=temp_dir, display_output=True)

        detector_exe = temp_dir / "build" / "detector"
        print("  - Running detector...")
        proc = subprocess.run([str(detector_exe)], check=True, capture_output=True, text=True)
        
        abi_details = {}
        for line in proc.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                abi_details[key.strip()] = value.strip()
        
        compiler = abi_details.get('compiler', 'unk_compiler')
        stdlib = abi_details.get('stdlib', 'unk_stdlib')
        
        # --- MODIFIED LOGIC FOR MACOS VERSIONING ---
        # On macOS, the OS version is more useful than the internal libc++ version.
        # But for the generic host detection, we still use the detected version.
        # The targeting logic will override this.
        if sys.platform == "darwin":
            # The C++ detector provides the internal _LIBCPP_VERSION
            stdlib_version = abi_details.get('stdlib_version', 'unk_stdlib_version')
            detected_os = "macos"
        else:
            # On Linux, this will be the glibc version
            stdlib_version = abi_details.get('stdlib_version', 'unk_stdlib_version')
            detected_os = abi_details.get("os", "linux")

        abi = abi_details.get('abi', 'unk_abi')
        abi_string = f"{compiler}-{stdlib}-{stdlib_version}-{abi}"
        
        arch = platform.machine()
        
        platform_identifier = {
            "triplet": f"{arch}-{detected_os}",
            "abi_signature": abi_string,
            "details": abi_details,
            "is_native": True,
            "cross_file": None,
            "docker_image": None,
            "arch": arch
        }

        with open(ABI_CACHE_FILE, 'w') as f:
            json.dump(platform_identifier, f, indent=2)
        
        print(f"✅ Native ABI detected and cached: {abi_string}")
        return platform_identifier

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def get_platform_identifier() -> dict:
    """
    Gets the native platform identifier, using a cached value if available.
    """
    if ABI_CACHE_FILE.exists():
        with open(ABI_CACHE_FILE, 'r') as f:
            return json.load(f)
    else:
        return _detect_and_cache_abi()

def get_macos_targeted_platform_identifier(target_version: str) -> dict:
    """
    Generates a platform identifier for a specific target macOS version.
    This bypasses host detection for the version string.
    """
    # We still need the host's compiler info, so we run detection if not cached.
    host_platform = get_platform_identifier()
    host_details = host_platform['details']

    compiler = host_details.get('compiler', 'clang')
    stdlib = host_details.get('stdlib', 'libc++')
    abi = host_details.get('abi', 'libc++_abi')
    arch = platform.machine()
    
    abi_string = f"{compiler}-{stdlib}-{target_version}-{abi}"

    return {
        "triplet": f"{arch}-macos",
        "abi_signature": abi_string,
        "details": {
            "os": "macos",
            "compiler": compiler,
            "compiler_version": host_details.get('compiler_version'),
            "stdlib": stdlib,
            "stdlib_version": target_version, # The key change is here
            "abi": abi,
        },
        "is_native": True,
        "cross_file": None,
        "docker_image": None,
        "arch": arch
    }

def get_available_build_targets() -> list:
    """Gets native, cross-compilation, and Docker build targets."""
    targets = [get_platform_identifier()]
    
    # Add cross-file targets
    CROSS_FILES_PATH.mkdir(exist_ok=True)
    for cross_file in CROSS_FILES_PATH.glob("*.cross"):
        triplet = cross_file.stem
        targets.append({
            "triplet": triplet,
            "abi_signature": f"cross-{triplet}",
            "is_native": False,
            "cross_file": str(cross_file.resolve()),
            "docker_image": None
        })
        
    # Add Docker targets if Docker is available
    if docker:
        try:
            client = docker.from_env()
            client.ping()
            for name, image in DOCKER_BUILD_IMAGES.items():
                arch = name.split(' ')[0]
                targets.append({
                    "triplet": f"{arch}-linux",
                    "abi_signature": f"docker-{image}",
                    "is_native": False,
                    "cross_file": None,
                    "docker_image": image,
                    "arch": arch
                })
        except Exception:
            typer.secho("Warning: Docker is installed but the daemon is not running. Docker targets are unavailable.", fg=typer.colors.YELLOW)
            
    return targets

def _build_plugin_for_target(sdist_path: Path, build_dir: Path, target: dict):
    """Builds a plugin natively or with a cross file."""
    source_dir = build_dir / "src"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    
    with zipfile.ZipFile(sdist_path, 'r') as sdist_zip:
        sdist_zip.extractall(source_dir)
        
        
    setup_cmd = ["meson", "setup"]
    if target["cross_file"]:
        setup_cmd.extend(["--cross-file", target["cross_file"]])
    setup_cmd.append("build")
    
    run_command(setup_cmd, cwd=source_dir, display_output=True)
    run_command(["meson", "compile", "-C", "build"], cwd=source_dir, display_output=True)
    
    meson_build_dir = source_dir / "build"
    compiled_lib = next(meson_build_dir.rglob("lib*.so"), None) or next(meson_build_dir.rglob("lib*.dylib"), None)
    if not compiled_lib:
        raise FileNotFoundError("Could not find compiled library after build.")
        
    return compiled_lib, target # Return target as ABI is pre-determined

def _build_plugin_in_docker(sdist_path: Path, build_dir: Path, target: dict, plugin_name: str):
    """Builds a plugin inside a Docker container."""
    client = docker.from_env()
    image_name = target["docker_image"]

    # Find arch from DOCKER_BUILD_IMAGES to create a clean triplet later
    arch = "unknown_arch"
    for name, img in DOCKER_BUILD_IMAGES.items():
        if img == image_name:
            arch = name.split(' ')[0]
            break
    
    typer.echo(f"  - Pulling Docker image '{image_name}' (if necessary)...")
    client.images.pull(image_name)

    source_dir = build_dir / "src"
    if source_dir.exists():
        shutil.rmtree(source_dir)
        
    with zipfile.ZipFile(sdist_path, 'r') as sdist_zip:
        sdist_zip.extractall(source_dir)
        
    # This script will be run inside the container
    build_script = f"""
    set -e
    echo "--- Installing build dependencies ---"
    export PATH="/opt/python/cp313-cp313/bin:$PATH"
    pip install meson ninja cmake

    echo "  -> ℹ meson version: $(meson --version) [$(which meson)]" 
    echo "  -> ℹ ninja version: $(ninja --version) [$(which ninja)]" 
    echo "  -> ℹ cmake version: $(cmake --version) [$(which cmake)]" 
    
    echo "--- Configuring with Meson ---"
    meson setup /build/meson_build
    echo "--- Compiling with Meson ---"
    meson compile -C /build/meson_build
    echo "--- Running ABI detector ---"
    # We need to build and run the ABI detector inside the container too
    mkdir /tmp/abi && cd /tmp/abi
    echo "{ABI_DETECTOR_CPP_SRC.replace('"', '\\"')}" > main.cpp
    echo "{ABI_DETECTOR_MESON_SRC.replace('"', '\\"')}" > meson.build
    meson setup build && meson compile -C build
    ./build/detector > /build/abi_details.txt
    """
    
    container_build_dir = Path("/build")
    
    typer.echo("  - Running build container...")
    container = client.containers.run(
        image=image_name,
        command=["/bin/sh", "-c", build_script],
        volumes={str(source_dir.resolve()): {'bind': str(container_build_dir), 'mode': 'rw'}},
        working_dir=str(container_build_dir),
        detach=True
    )
    
    # Stream logs
    for line in container.logs(stream=True, follow=True):
        typer.echo(f"    [docker] {line.decode('utf-8').strip()}")
        
    result = container.wait()
    if result["StatusCode"] != 0:
        # The container is stopped, but we can still inspect its filesystem by restarting it briefly.
        log_output = container.logs()
        container.remove() # Clean up before raising
        typer.secho(f"Build failed inside Docker. Full log:\n{log_output.decode('utf-8')}", fg=typer.colors.RED)
        raise subprocess.CalledProcessError(result["StatusCode"], "Build inside Docker failed.")

    # Retrieve artifacts by searching inside the container's filesystem
    typer.echo("  - Locating compiled library in container...")
    meson_build_dir_str = (container_build_dir / "meson_build").as_posix()
    expected_lib_name = f"lib{plugin_name}.so"
    
    find_cmd = f"find {meson_build_dir_str} -name {expected_lib_name}"
    
    # We need to run the find command in the now-stopped container.
    # We can't use exec_run on a stopped container, but we can create a new
    # one that uses the same filesystem (volume) to find the file.
    try:
        find_output = client.containers.run(
            image=image_name,
            command=["/bin/sh", "-c", find_cmd],
            volumes={str(source_dir.resolve()): {'bind': str(container_build_dir), 'mode': 'ro'}},
            remove=True, # Clean up the find container immediately
            detach=False
        )
        found_path_str = find_output.decode('utf-8').strip()
        if not found_path_str:
             raise FileNotFoundError("Find command returned no path.")
        compiled_lib = Path(found_path_str)
        typer.echo(f"  - Found library at: {compiled_lib}")

    except Exception as e:
        typer.secho(f"  - Error: Could not locate '{expected_lib_name}' inside the container.", fg=typer.colors.RED)
        typer.secho(f"    Details: {e}", fg=typer.colors.RED)
        raise FileNotFoundError("Could not find compiled library in container after a successful build.")
        
    # Get the ABI details from the container
    abi_details_content = ""
    bits, _ = container.get_archive(str(container_build_dir / "abi_details.txt"))
    for chunk in bits:
        abi_details_content += chunk.decode('utf-8')
    
    # We need to find the actual file content within the tar stream
    # This is a simplification; a real implementation would use the `tarfile` module
    actual_content = abi_details_content.split('\n', 1)[1] if '\n' in abi_details_content else abi_details_content
    actual_content = actual_content.split('main.cpp')[1].strip() if 'main.cpp' in actual_content else actual_content
    actual_content = actual_content.rsplit('0755', 1)[0].strip() if '0755' in actual_content else actual_content


    abi_details = {}
    for line in actual_content.strip().split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            abi_details[key.strip()] = value.strip()
    
    compiler = abi_details.get('compiler', 'unk_compiler')
    stdlib = abi_details.get('stdlib', 'unk_stdlib')
    stdlib_version = abi_details.get('stdlib_version', 'unk_stdlib_version')
    abi = abi_details.get('abi', 'unk_abi')
    abi_string = f"{compiler}-{stdlib}-{stdlib_version}-{abi}"
    
    final_target = {
        "triplet": f"{arch}-{abi_details.get('os', 'linux')}",
        "abi_signature": abi_string,
        "is_native": False,
        "cross_file": None,
        "docker_image": image_name,
        "arch": arch
    }
    
    # Copy the binary out
    local_lib_path = build_dir / compiled_lib.name
    bits, _ = container.get_archive(str(compiled_lib))
    with open(local_lib_path, 'wb') as f:
        for chunk in bits:
            f.write(chunk)
            
    container.remove()
    
    return local_lib_path, final_target


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
