# fourdst/cli/main.py

import typer
import os
import sys
import shutil
import subprocess
from pathlib import Path
import importlib.resources
import questionary
import yaml
import zipfile
import hashlib
import platform
import datetime
import json

# --- Third-party libraries required for new features ---
# These would need to be added to the project's dependencies (e.g., in pyproject.toml)
try:
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa, ed25519
    from cryptography.exceptions import InvalidSignature
except ImportError:
    print("Error: This CLI now requires 'cryptography' and 'PyYAML'. Please install them.", file=sys.stderr)
    print("Run: pip install cryptography pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    import docker
except ImportError:
    docker = None # Docker is an optional dependency for the 'fill' command

# --- Main Typer application ---
app = typer.Typer(
    name="fourdst-cli",
    help="A command-line tool for managing fourdst projects, plugins, and bundles."
)
plugin_app = typer.Typer(name="plugin", help="Commands for managing individual fourdst plugins.")
bundle_app = typer.Typer(name="bundle", help="Commands for creating, signing, and managing plugin bundles.")
keys_app = typer.Typer(name="keys", help="Commands for cryptographic key generation and management.")
cache_app = typer.Typer(name="cache", help="Commands for managing the local cache.")

app.add_typer(plugin_app, name="plugin")
app.add_typer(bundle_app, name="bundle")
app.add_typer(keys_app, name="keys")
app.add_typer(cache_app, name="cache")


# --- Configuration ---
FOURDST_CONFIG_DIR = Path.home() / ".config" / "fourdst"
LOCAL_TRUST_STORE_PATH = FOURDST_CONFIG_DIR / "keys"
CROSS_FILES_PATH = FOURDST_CONFIG_DIR / "cross"
CACHE_PATH = FOURDST_CONFIG_DIR / "cache"
ABI_CACHE_FILE = CACHE_PATH / "abi_identifier.json"
DOCKER_BUILD_IMAGES = {
    "x86_64 (manylinux_2_28)": "quay.io/pypa/manylinux_2_28_x86_64",
    "aarch64 (manylinux_2_28)": "quay.io/pypa/manylinux_2_28_aarch64",
    "i686 (manylinux_2_28)" : "quay.io/pypa/manylinux_2_28_i686",
    "ppc64le (manylinux_2_28)" : "quay.io/pypa/manylinux_2_28_ppc64le",
    "s390x (manylinux_2_28)" : "quay.io/pypa/manylinux_2_28_s390x"
}

# --- C++ ABI Detector Source ---
ABI_DETECTOR_CPP_SRC = """
#include <iostream>
#include <string>
#include <vector>

#ifdef __GNUC__
#if __has_include(<gnu/libc-version.h>)
#include <gnu/libc-version.h>
#endif
#endif

int main() {
    std::string os;
    std::string compiler;
    std::string compiler_version;
    std::string stdlib;
    std::string stdlib_version;
    std::string abi;

#if defined(__APPLE__) && defined(__MACH__)
    os = "macos";
#elif defined(__linux__)
    os = "linux";
#elif defined(_WIN32)
    os = "windows";
#else
    os = "unknown_os";
#endif

#if defined(__clang__)
    compiler = "clang";
    compiler_version = __clang_version__;
#elif defined(__GNUC__)
    compiler = "gcc";
    compiler_version = std::to_string(__GNUC__) + "." + std::to_string(__GNUC_MINOR__) + "." + std::to_string(__GNUC_PATCHLEVEL__);
#elif defined(_MSC_VER)
    compiler = "msvc";
    compiler_version = std::to_string(_MSC_VER);
#else
    compiler = "unknown_compiler";
    compiler_version = "0";
#endif

#if defined(_LIBCPP_VERSION)
    stdlib = "libc++";
    stdlib_version = std::to_string(_LIBCPP_VERSION);
    abi = "libc++_abi"; // On libc++, the ABI is tightly coupled with the library itself.
#elif defined(__GLIBCXX__)
    stdlib = "libstdc++";
    #if defined(_GLIBCXX_USE_CXX11_ABI)
        abi = _GLIBCXX_USE_CXX11_ABI == 1 ? "cxx11_abi" : "pre_cxx11_abi";
    #else
        abi = "pre_cxx11_abi";
    #endif
    #if __has_include(<gnu/libc-version.h>)
        stdlib_version = gnu_get_libc_version();
    #else
        stdlib_version = "unknown";
    #endif
#else
    stdlib = "unknown_stdlib";
    abi = "unknown_abi";
#endif

    std::cout << "os=" << os << std::endl;
    std::cout << "compiler=" << compiler << std::endl;
    std::cout << "compiler_version=" << compiler_version << std::endl;
    std::cout << "stdlib=" << stdlib << std::endl;
    if (!stdlib_version.empty()) {
        std::cout << "stdlib_version=" << stdlib_version << std::endl;
    }
    // Always print the ABI key for consistent parsing
    std::cout << "abi=" << abi << std::endl;

    return 0;
}
"""

ABI_DETECTOR_MESON_SRC = """
project('abi-detector', 'cpp', default_options : ['cpp_std=c++23'])
executable('detector', 'main.cpp')
"""

# --- .gitignore Template ---
GITIGNORE_CONTENT = """# General
*.swp
*~
.DS_Store

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
.venv/
venv/
env/
*.egg-info/
dist/

# C++ Build Artifacts
*.o
*.a
*.so
*.dylib
*.dll
*.lib
*.exe

# Meson Build System
# Ignore any directory containing meson-private, which is a reliable marker
**/meson-private/
# Also ignore common build directory names
build/
builddir/

# Subprojects - ignore all subdirectories except 'packagefiles' and root .wrap files
/subprojects/*
!/subprojects/packagefiles
!/subprojects/*.wrap

# Editor specific
.vscode/
.idea/
*.sublime-project
*.sublime-workspace
"""


# --- Helper Functions ---

def get_template_content(template_name: str) -> str:
    """Safely reads content from a template file packaged with the CLI."""
    try:
        return importlib.resources.files('fourdst.cli.templates').joinpath(template_name).read_text()
    except FileNotFoundError:
        print(f"Error: Template file '{template_name}' not found.", file=sys.stderr)
        sys.exit(1)

def _detect_and_cache_abi(cross_file: Path = None):
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
        run_command(["meson", "setup", "build"], cwd=temp_dir)
        print("  - Compiling detector...")
        run_command(["meson", "compile", "-C", "build"], cwd=temp_dir)

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
        stdlib_version = abi_details.get('stdlib_version', 'unk_stdlib_version')
        abi = abi_details.get('abi', 'unk_abi')
        abi_string = f"{compiler}-{stdlib}-{stdlib_version}-{abi}"
        
        detected_os = abi_details.get("os", "unknown_os")
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
                    "triplet": f"linux-{arch}",
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
        
    meson_build_dir = build_dir / "meson_build"
    if meson_build_dir.exists():
        shutil.rmtree(meson_build_dir)
        
    setup_cmd = ["meson", "setup"]
    if target["cross_file"]:
        setup_cmd.extend(["--cross-file", target["cross_file"]])
    setup_cmd.append(str(meson_build_dir))
    
    run_command(setup_cmd, cwd=source_dir)
    run_command(["meson", "compile", "-C", str(meson_build_dir)], cwd=source_dir)
    
    compiled_lib = next(meson_build_dir.glob("lib*.so"), None) or next(meson_build_dir.glob("lib*.dylib"), None)
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
        "triplet": f"{abi_details.get('os', 'linux')}-{arch}",
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


def calculate_sha256(file_path: Path) -> str:
    """Calculates the SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def run_command(command: list[str], cwd: Path = None, check=True):
    """Runs a command and handles errors."""
    try:
        # Hide stdout/stderr unless there's an error
        result = subprocess.run(command, check=check, capture_output=True, text=True, cwd=cwd)
        return result
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Error running command: {' '.join(command)}", file=sys.stderr)
            print(f"STDOUT:\n{e.stdout}", file=sys.stderr)
            print(f"STDERR:\n{e.stderr}", file=sys.stderr)
            raise typer.Exit(code=1)
        return e


# --- Cache Management Commands ---
@cache_app.command("clear")
def cache_clear():
    """
    Clears all cached data, including the ABI signature.
    Run this if you have updated your C++ compiler.
    """
    if CACHE_PATH.exists():
        shutil.rmtree(CACHE_PATH)
        print("✅ Local cache cleared.")
    else:
        print("No cache found to clear.")

# --- Key Management Commands ---

@keys_app.command("generate")
def keys_generate(
    key_name: str = typer.Option("author_key", "--name", "-n", help="The base name for the generated key files.")
):
    """
    Generates a new Ed25519 key pair for signing bundles.
    """
    private_key_path = Path(f"{key_name}")
    public_key_path = Path(f"{key_name}.pub")

    if private_key_path.exists() or public_key_path.exists():
        print(f"Error: Key files '{private_key_path}' or '{public_key_path}' already exist.", file=sys.stderr)
        raise typer.Exit(code=1)

    print("Generating Ed25519 key pair...")
    run_command([
        "ssh-keygen",
        "-t", "ed25519",
        "-f", str(private_key_path),
        "-N", "", # No passphrase
        "-C", "fourdst bundle signing key"
    ])
    print("\n✅ Keys generated successfully!")
    print(f"  -> Private Key (KEEP SECRET): {private_key_path.resolve()}")
    print(f"  -> Public Key (SHARE): {public_key_path.resolve()}")
    print("\nShare the public key with users who need to trust your bundles.")

@keys_app.command("sync")
def keys_sync(
    repo_url: str = typer.Argument(..., help="The URL of the Git repository containing trusted public keys.")
):
    """
    Syncs the local trust store with a central Git repository of public keys.
    This will ADD new keys and REMOVE keys that are no longer in the repository.
    """
    LOCAL_TRUST_STORE_PATH.mkdir(parents=True, exist_ok=True)
    temp_dir = Path("temp_keys_repo")

    print(f"Syncing trust store with {repo_url}...")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    run_command(["git", "clone", "--depth", "1", repo_url, str(temp_dir)])

    # Get key sets
    repo_keys = {p.name for p in temp_dir.glob("*.pub")}
    local_keys = {p.name for p in LOCAL_TRUST_STORE_PATH.glob("*.pub")}

    # Sync logic
    keys_to_add = repo_keys - local_keys
    keys_to_remove = local_keys - repo_keys

    for key_file in keys_to_add:
        shutil.copy(temp_dir / key_file, LOCAL_TRUST_STORE_PATH / key_file)
        print(f"  [+] Added trusted key: {key_file}")

    for key_file in keys_to_remove:
        (LOCAL_TRUST_STORE_PATH / key_file).unlink()
        print(f"  [-] Removed key: {key_file}")

    if not keys_to_add and not keys_to_remove:
        print("Trust store is already up to date.")

    shutil.rmtree(temp_dir)
    print("\n✅ Trust store sync complete!")
    print(f"Location: {LOCAL_TRUST_STORE_PATH}")


# --- Bundle Management Commands ---

@bundle_app.command("create")
def bundle_create(
    plugin_dirs: list[Path] = typer.Argument(..., help="A list of plugin project directories to include.", exists=True, file_okay=False),
    output_bundle: Path = typer.Option("bundle.fbundle", "--out", "-o", help="The path for the output bundle file."),
    bundle_name: str = typer.Option("MyPluginBundle", "--name", help="The name of the bundle."),
    bundle_version: str = typer.Option("0.1.0", "--ver", help="The version of the bundle."),
    bundle_author: str = typer.Option("Unknown", "--author", help="The author of the bundle.")
):
    """
    Builds and packages one or more plugin projects into a single .fbundle file.
    """
    staging_dir = Path("temp_bundle_staging")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir()

    # Get the host platform identifier, triggering detection if needed.
    host_platform = get_platform_identifier()
    abi_tag = host_platform["abi_signature"]

    manifest = {
        "bundleName": bundle_name,
        "bundleVersion": bundle_version,
        "bundleAuthor": bundle_author,
        "bundleComment": "Created with fourdst-cli",
        "bundledOn": datetime.datetime.now().isoformat(),
        "bundlePlugins": {}
    }
    
    print("Creating bundle...")
    for plugin_dir in plugin_dirs:
        plugin_name = plugin_dir.name
        print(f"--> Processing plugin: {plugin_name}")

        # 1. Build the plugin
        print(f"    - Compiling for host platform...")
        build_dir = plugin_dir / "builddir"
        if not build_dir.exists():
            run_command(["meson", "setup", "builddir"], cwd=plugin_dir)
        run_command(["meson", "compile", "-C", "builddir"], cwd=plugin_dir)

        # 2. Find the compiled artifact
        compiled_lib = next(build_dir.glob("lib*.so"), None) or next(build_dir.glob("lib*.dylib"), None)
        if not compiled_lib:
            print(f"Error: Could not find compiled library for {plugin_name} (expected lib*.so or lib*.dylib)", file=sys.stderr)
            raise typer.Exit(code=1)

        # 3. Package source code (sdist), respecting .gitignore
        print("    - Packaging source code (respecting .gitignore)...")
        sdist_path = staging_dir / f"{plugin_name}_src.zip"
        
        # Use git to list files, which automatically respects .gitignore
        git_check = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=plugin_dir, check=False)
        
        files_to_include = []
        if git_check.returncode == 0:
            # This is a git repo, use git to list files
            result = run_command(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=plugin_dir)
            files_to_include = [plugin_dir / f for f in result.stdout.strip().split('\n') if f]
        else:
            # Not a git repo, fall back to os.walk and warn the user
            typer.secho(f"    - Warning: '{plugin_dir.name}' is not a git repository. Packaging all files.", fg=typer.colors.YELLOW)
            for root, _, files in os.walk(plugin_dir):
                if 'builddir' in root:
                    continue
                for file in files:
                    files_to_include.append(Path(root) / file)

        with zipfile.ZipFile(sdist_path, 'w', zipfile.ZIP_DEFLATED) as sdist_zip:
            for file_path in files_to_include:
                if file_path.is_file():
                    sdist_zip.write(file_path, file_path.relative_to(plugin_dir))

        # 4. Stage artifacts with ABI-tagged filenames and update manifest
        binaries_dir = staging_dir / "bin"
        binaries_dir.mkdir(exist_ok=True)
        
        # Construct new filename with arch, os, and ABI tag
        base_name = compiled_lib.stem # e.g., "libplugin_a"
        ext = compiled_lib.suffix     # e.g., ".so"
        triplet = host_platform["triplet"]
        abi_signature = host_platform["abi_signature"]
        tagged_filename = f"{base_name}.{triplet}.{abi_signature}{ext}"
        staged_lib_path = binaries_dir / tagged_filename
        
        print(f"    - Staging binary as: {tagged_filename}")
        shutil.copy(compiled_lib, staged_lib_path)

        manifest["bundlePlugins"][plugin_name] = {
            "sdist": {
                "path": sdist_path.name,
                "sdistBundledOn": datetime.datetime.now().isoformat(),
                "buildable": True
            },
            "binaries": [{
                "platform": {
                    "triplet": host_platform["triplet"],
                    "abi_signature": host_platform["abi_signature"]
                },
                "path": staged_lib_path.relative_to(staging_dir).as_posix(),
                "compiledOn": datetime.datetime.now().isoformat()
            }]
        }

    # 5. Write manifest and package final bundle
    manifest_path = staging_dir / "manifest.yaml"
    with open(manifest_path, 'w') as f:
        yaml.dump(manifest, f, sort_keys=False)

    print(f"\nPackaging final bundle: {output_bundle}")
    with zipfile.ZipFile(output_bundle, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
        for root, _, files in os.walk(staging_dir):
            for file in files:
                file_path = Path(root) / file
                bundle_zip.write(file_path, file_path.relative_to(staging_dir))

    shutil.rmtree(staging_dir)
    print("\n✅ Bundle created successfully!")

@bundle_app.command("fill")
def bundle_fill(bundle_path: Path = typer.Argument(..., help="The .fbundle file to fill with new binaries.", exists=True)):
    """
    Builds new binaries for the current host or cross-targets from the bundle's source.
    """
    staging_dir = Path(f"temp_fill_{bundle_path.stem}")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    
    try:
        # 1. Unpack and load manifest
        with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
            bundle_zip.extractall(staging_dir)

        manifest_path = staging_dir / "manifest.yaml"
        if not manifest_path.exists():
            typer.secho("Error: Bundle is invalid. Missing manifest.yaml.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)

        # 2. Find available targets and missing binaries
        available_targets = get_available_build_targets()
        build_options = []
        
        for plugin_name, plugin_data in manifest.get('bundlePlugins', {}).items():
            if "sdist" not in plugin_data:
                continue # Cannot build without source
            
            existing_abis = {b['platform']['abi_signature'] for b in plugin_data.get('binaries', [])}
            
            for target in available_targets:
                # Use a more descriptive name for the choice
                if target.get('docker_image', None):
                    display_name = f"Docker: {target['docker_image']}"
                elif target.get('cross_file', None):
                    display_name = f"Cross: {Path(target['cross_file']).name}"
                else:
                    display_name = f"Native: {target['abi_signature']}"

                if target['abi_signature'] not in existing_abis:
                    build_options.append({
                        "name": f"Build '{plugin_name}' for {display_name}",
                        "plugin_name": plugin_name,
                        "target": target
                    })
        
        if not build_options:
            typer.secho("✅ Bundle is already full for all available build targets.", fg=typer.colors.GREEN)
            raise typer.Exit()
            
        # 3. Prompt user to select which targets to build
        choices = [opt['name'] for opt in build_options]
        selected_builds = questionary.checkbox("Select which missing binaries to build:", choices=choices).ask()
        
        if not selected_builds:
            typer.echo("No binaries selected to build. Exiting.")
            raise typer.Exit()
            
        # 4. Build selected targets
        for build_name in selected_builds:
            build_job = next(opt for opt in build_options if opt['name'] == build_name)
            plugin_name = build_job['plugin_name']
            target = build_job['target']
            
            typer.secho(f"\nBuilding {plugin_name} for target '{build_name}'...", bold=True)
            
            sdist_zip_path = staging_dir / manifest['bundlePlugins'][plugin_name]['sdist']['path']
            build_temp_dir = staging_dir / f"build_{plugin_name}"

            try:
                if target['docker_image']:
                    if not docker:
                        typer.secho("Error: Docker is not installed. Please install Docker to build this target.", fg=typer.colors.RED)
                        continue
                    compiled_lib, final_target = _build_plugin_in_docker(sdist_zip_path, build_temp_dir, target, plugin_name)
                else:
                    compiled_lib, final_target = _build_plugin_for_target(sdist_zip_path, build_temp_dir, target)
                
                # Add new binary to bundle
                abi_tag = final_target["abi_signature"]
                base_name = compiled_lib.stem
                ext = compiled_lib.suffix
                triplet = final_target["triplet"]
                tagged_filename = f"{base_name}.{triplet}.{abi_tag}{ext}"
                
                binaries_dir = staging_dir / "bin"
                binaries_dir.mkdir(exist_ok=True)
                staged_lib_path = binaries_dir / tagged_filename
                shutil.move(compiled_lib, staged_lib_path)
                
                # Update manifest
                new_binary_entry = {
                    "platform": {
                        "triplet": final_target["triplet"],
                        "abi_signature": abi_tag,
                        "arch": final_target["arch"]
                    },
                    "path": staged_lib_path.relative_to(staging_dir).as_posix(),
                    "compiledOn": datetime.datetime.now().isoformat()
                }
                manifest['bundlePlugins'][plugin_name]['binaries'].append(new_binary_entry)
                typer.secho(f"  -> Successfully built and staged {tagged_filename}", fg=typer.colors.GREEN)

            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                typer.secho(f"  -> Failed to build {plugin_name} for target '{build_name}': {e}", fg=typer.colors.RED)
            finally:
                if build_temp_dir.exists():
                    shutil.rmtree(build_temp_dir)

        # 5. Repackage the bundle
        # Invalidate any old signature
        if "bundleAuthorKeyFingerprint" in manifest:
            del manifest["bundleAuthorKeyFingerprint"]
            if (staging_dir / "manifest.sig").exists():
                (staging_dir / "manifest.sig").unlink()
            typer.secho("\n⚠️ Bundle signature has been invalidated by this operation. Please re-sign the bundle.", fg=typer.colors.YELLOW)

        with open(manifest_path, 'w') as f:
            yaml.dump(manifest, f, sort_keys=False)
            
        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
            for file_path in staging_dir.rglob('*'):
                if file_path.is_file():
                    bundle_zip.write(file_path, file_path.relative_to(staging_dir))
        
        typer.secho(f"\n✅ Bundle '{bundle_path.name}' has been filled successfully.", fg=typer.colors.GREEN)

    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)


@bundle_app.command("sign")
def bundle_sign(
    bundle_path: Path = typer.Argument(..., help="The .fbundle file to sign.", exists=True),
    private_key: Path = typer.Option(..., "--key", "-k", help="Path to the author's private signing key.", exists=True)
):
    """
    Signs a bundle with an author's private key, adding checksums and a signature.
    """
    print(f"Signing bundle: {bundle_path}")
    staging_dir = Path("temp_sign_staging")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)

    # 1. Unpack the bundle
    with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
        bundle_zip.extractall(staging_dir)

    manifest_path = staging_dir / "manifest.yaml"
    if not manifest_path.exists():
        print("Error: manifest.yaml not found in bundle.", file=sys.stderr)
        raise typer.Exit(code=1)

    # 2. Load private key and derive public key to get fingerprint
    with open(private_key, "rb") as key_file:
        priv_key_obj = serialization.load_ssh_private_key(key_file.read(), password=None)
    
    pub_key_obj = priv_key_obj.public_key()
    pub_key_bytes = pub_key_obj.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )
    fingerprint = "sha256:" + hashlib.sha256(pub_key_bytes).hexdigest()
    print(f"  - Signing with key fingerprint: {fingerprint}")

    # 3. Update manifest with checksums and fingerprint
    with open(manifest_path, 'r') as f:
        manifest = yaml.safe_load(f)

    manifest['bundleAuthorKeyFingerprint'] = fingerprint
    for plugin in manifest['bundlePlugins'].values():
        for binary in plugin.get('binaries', []):
            binary_path = staging_dir / binary['path']
            if binary_path.exists():
                 binary['checksum'] = "sha256:" + calculate_sha256(binary_path)
            else:
                 binary['checksum'] = "MISSING_FILE"


    with open(manifest_path, 'w') as f:
        yaml.dump(manifest, f, sort_keys=False)
    print("  - Added file checksums and key fingerprint to manifest.")

    # 4. Sign the manifest
    manifest_content = manifest_path.read_bytes()
    
    if isinstance(priv_key_obj, ed25519.Ed25519PrivateKey):
        signature = priv_key_obj.sign(manifest_content)
    elif isinstance(priv_key_obj, rsa.RSAPrivateKey):
        signature = priv_key_obj.sign(
            manifest_content,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    else:
        print("Error: Unsupported private key type for signing.", file=sys.stderr)
        raise typer.Exit(code=1)


    sig_path = staging_dir / "manifest.sig"
    sig_path.write_bytes(signature)
    print("  - Created manifest.sig.")

    # 5. Repackage the bundle
    with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
        for file_path in staging_dir.rglob('*'):
            if file_path.is_file():
                bundle_zip.write(file_path, file_path.relative_to(staging_dir))

    shutil.rmtree(staging_dir)
    print("\n✅ Bundle signed successfully!")

@bundle_app.command("inspect")
def bundle_inspect(bundle_path: Path = typer.Argument(..., help="The .fbundle file to inspect.", exists=True)):
    """
    Inspects a bundle, validating its contents and cryptographic signature.
    """
    staging_dir = Path(f"temp_inspect_{bundle_path.stem}")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    
    try:
        # 1. Unpack and load manifest
        with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
            archive_files = set(bundle_zip.namelist())
            bundle_zip.extractall(staging_dir)

        manifest_path = staging_dir / "manifest.yaml"
        if not manifest_path.exists():
            typer.secho("Error: Bundle is invalid. Missing manifest.yaml.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)

        # 2. Print Header
        typer.secho(f"--- Bundle Inspection Report for: {bundle_path.name} ---", bold=True)
        typer.echo(f"Name:     {manifest.get('bundleName', 'N/A')}")
        typer.echo(f"Version:  {manifest.get('bundleVersion', 'N/A')}")
        typer.echo(f"Author:   {manifest.get('bundleAuthor', 'N/A')}")
        typer.echo(f"Bundled:  {manifest.get('bundledOn', 'N/A')}")
        typer.echo("-" * 50)

        # 3. Signature and Trust Verification
        fingerprint = manifest.get('bundleAuthorKeyFingerprint')
        sig_path = staging_dir / "manifest.sig"
        
        if not fingerprint or not sig_path.exists():
            typer.secho("Trust Status: 🟡 UNSIGNED", fg=typer.colors.YELLOW)
        else:
            # Find the key in the local trust store
            trusted_key_path = None
            if LOCAL_TRUST_STORE_PATH.exists():
                for key_file in LOCAL_TRUST_STORE_PATH.glob("*.pub"):
                    pub_key_bytes = key_file.read_bytes()
                    pub_key_fingerprint = "sha256:" + hashlib.sha256(pub_key_bytes).hexdigest()
                    if pub_key_fingerprint == fingerprint:
                        trusted_key_path = key_file
                        break
            
            if not trusted_key_path:
                typer.secho(f"Trust Status: ⚠️ SIGNED but UNTRUSTED AUTHOR ({fingerprint})", fg=typer.colors.YELLOW)
            else:
                try:
                    pub_key_obj = serialization.load_ssh_public_key(trusted_key_path.read_bytes())
                    signature = sig_path.read_bytes()
                    manifest_content = manifest_path.read_bytes()

                    if isinstance(pub_key_obj, ed25519.Ed25519PublicKey):
                        pub_key_obj.verify(signature, manifest_content)
                    elif isinstance(pub_key_obj, rsa.RSAPublicKey):
                         pub_key_obj.verify(
                            signature,
                            manifest_content,
                            padding.PKCS1v15(),
                            hashes.SHA256()
                        )
                    typer.secho(f"Trust Status: ✅ SIGNED and TRUSTED ({fingerprint})", fg=typer.colors.GREEN)
                except InvalidSignature:
                    typer.secho(f"Trust Status: ❌ INVALID SIGNATURE ({fingerprint})", fg=typer.colors.RED)
        
        typer.echo("-" * 50)

        # 4. Content Validation
        typer.echo("Validating bundle contents...")
        missing_files = []
        checksum_errors = []

        for plugin_name, plugin_data in manifest.get('bundlePlugins', {}).items():
            sdist_path = plugin_data.get('sdist', {}).get('path')
            if sdist_path and sdist_path not in archive_files:
                missing_files.append(sdist_path)
            
            for binary in plugin_data.get('binaries', []):
                binary_path_str = binary.get('path')
                if binary_path_str and binary_path_str not in archive_files:
                    missing_files.append(binary_path_str)
                elif binary_path_str:
                    # Verify checksum if present
                    expected_checksum = binary.get('checksum')
                    if expected_checksum:
                        actual_checksum = "sha256:" + calculate_sha256(staging_dir / binary_path_str)
                        if actual_checksum != expected_checksum:
                            checksum_errors.append(binary_path_str)

        if not missing_files and not checksum_errors:
            typer.secho("Content Validation: ✅ OK", fg=typer.colors.GREEN)
        else:
            typer.secho("Content Validation: ❌ FAILED", fg=typer.colors.RED)
            for f in missing_files:
                typer.echo(f"  - Missing file from archive: {f}")
            for f in checksum_errors:
                typer.echo(f"  - Checksum mismatch for: {f}")

        # 5. Plugin Details
        typer.echo("-" * 50)
        typer.secho("Available Plugins:", bold=True)
        for plugin_name, plugin_data in manifest.get('bundlePlugins', {}).items():
            typer.echo(f"\n  Plugin: {plugin_name}")
            typer.echo(f"    Source Dist: {plugin_data.get('sdist', {}).get('path', 'N/A')}")
            binaries = plugin_data.get('binaries', [])
            if not binaries:
                typer.echo("    Binaries: None")
            else:
                typer.echo("    Binaries:")
                for b in binaries:
                    plat = b.get('platform', {})
                    typer.echo(f"      - Path: {b.get('path', 'N/A')}")
                    typer.echo(f"        ABI:  {plat.get('abi_signature', 'N/A')}")
                    typer.echo(f"        Arch: {plat.get('triplet', 'N/A')}")

    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)


# --- Original Plugin Commands (Unchanged for now) ---

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


if __name__ == "__main__":
    # Create config directory if it doesn't exist
    CACHE_PATH.mkdir(parents=True, exist_ok=True)
    app()
