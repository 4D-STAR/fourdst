# fourdst/core/build.py

import os
import subprocess
import zipfile
import io
import tarfile
from pathlib import Path

try:
    import docker
except ImportError:
    docker = None

from fourdst.core.utils import run_command
from fourdst.core.platform import get_platform_identifier, get_macos_targeted_platform_identifier
from fourdst.core.config import CROSS_FILES_PATH, DOCKER_BUILD_IMAGES

def get_available_build_targets(progress_callback=None):
    """Gets native, cross-compilation, and Docker build targets."""
    def report_progress(message):
        if progress_callback:
            progress_callback(message)

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
            "docker_image": None,
            'type': 'cross'
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
                    "arch": arch,
                    'type': 'docker'
                })
        except Exception:
            report_progress("Warning: Docker is installed but the daemon is not running. Docker targets are unavailable.")
            
    return targets

def build_plugin_for_target(sdist_path: Path, build_dir: Path, target: dict, progress_callback=None):
    """Builds a plugin natively or with a cross file."""
    def report_progress(message):
        if progress_callback:
            progress_callback(message)

    source_dir = build_dir / "src"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    
    with zipfile.ZipFile(sdist_path, 'r') as sdist_zip:
        sdist_zip.extractall(source_dir)
        
    setup_cmd = ["meson", "setup"]
    if target.get("cross_file"):
        setup_cmd.extend(["--cross-file", target["cross_file"]])
    setup_cmd.append("build")
    
    run_command(setup_cmd, cwd=source_dir, progress_callback=progress_callback)
    run_command(["meson", "compile", "-C", "build"], cwd=source_dir, progress_callback=progress_callback)
    
    meson_build_dir = source_dir / "build"
    compiled_lib = next(meson_build_dir.rglob("lib*.so"), None) or next(meson_build_dir.rglob("lib*.dylib"), None)
    if not compiled_lib:
        raise FileNotFoundError("Could not find compiled library after build.")
        
    return compiled_lib, target

def build_plugin_in_docker(sdist_path: Path, build_dir: Path, target: dict, plugin_name: str, progress_callback=None):
    """Builds a plugin inside a Docker container."""
    def report_progress(message):
        if progress_callback:
            progress_callback(message)

    client = docker.from_env()
    image_name = target["docker_image"]

    arch = target.get("arch", "unknown_arch")
    
    report_progress(f"  - Pulling Docker image '{image_name}' (if necessary)...")
    client.images.pull(image_name)

    source_dir = build_dir / "src"
    if source_dir.exists():
        shutil.rmtree(source_dir)
        
    with zipfile.ZipFile(sdist_path, 'r') as sdist_zip:
        sdist_zip.extractall(source_dir)
        
    from fourdst.core.platform import ABI_DETECTOR_CPP_SRC, ABI_DETECTOR_MESON_SRC
    build_script = f"""
    set -e
    echo \"--- Installing build dependencies ---\"
    export PATH=\"/opt/python/cp313-cp313/bin:$PATH\"
    dnf install -y openssl-devel
    pip install meson ninja cmake
    
    echo \"--- Configuring with Meson ---\"
    meson setup /build/meson_build
    echo \"--- Compiling with Meson ---\"
    meson compile -C /build/meson_build
    echo \"--- Running ABI detector ---\"
    mkdir /tmp/abi && cd /tmp/abi
    echo \"{ABI_DETECTOR_CPP_SRC.replace('"', '\\"')}\" > main.cpp
    echo \"{ABI_DETECTOR_MESON_SRC.replace('"', '\\"')}\" > meson.build
    meson setup build && meson compile -C build
    ./build/detector > /build/abi_details.txt
    """
    
    container_build_dir = Path("/build")
    
    report_progress("  - Running build container...")
    container = client.containers.run(
        image=image_name,
        command=["/bin/sh", "-c", build_script],
        volumes={str(source_dir.resolve()): {'bind': str(container_build_dir), 'mode': 'rw'}},
        working_dir=str(container_build_dir),
        detach=True
    )
    
    for line in container.logs(stream=True, follow=True):
        report_progress(f"    [docker] {line.decode('utf-8').strip()}")
        
    result = container.wait()
    if result["StatusCode"] != 0:
        log_output = container.logs()
        container.remove()
        raise subprocess.CalledProcessError(result["StatusCode"], f"Build inside Docker failed. Full log:\n{log_output.decode('utf-8')}")

    report_progress("  - Locating compiled library in container...")
    meson_build_dir_str = (container_build_dir / "meson_build").as_posix()
    expected_lib_name = f"lib{plugin_name}.so"
    
    find_cmd = f"find {meson_build_dir_str} -name {expected_lib_name}"
    
    find_output = client.containers.run(
        image=image_name,
        command=["/bin/sh", "-c", find_cmd],
        volumes={str(source_dir.resolve()): {'bind': str(container_build_dir), 'mode': 'ro'}},
        remove=True,
        detach=False
    )
    found_path_str = find_output.decode('utf-8').strip()
    if not found_path_str:
            raise FileNotFoundError(f"Could not locate '{expected_lib_name}' inside the container.")
    compiled_lib_path_in_container = Path(found_path_str)

    # Use the tarfile module for robust extraction
    bits, _ = container.get_archive(str(container_build_dir / "abi_details.txt"))
    with tarfile.open(fileobj=io.BytesIO(b''.join(bits))) as tar:
        extracted_file = None
        for member in tar.getmembers():
            if member.isfile():
                extracted_file = tar.extractfile(member)
                break
        if not extracted_file:
            raise FileNotFoundError("Could not extract abi_details.txt from container archive.")
        abi_details_content = extracted_file.read()
    
    abi_details = {}
    for line in abi_details_content.decode('utf-8').strip().split('\n'):
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
    
    local_lib_path = build_dir / compiled_lib_path_in_container.name
    bits, _ = container.get_archive(str(compiled_lib_path_in_container))
    with tarfile.open(fileobj=io.BytesIO(b''.join(bits))) as tar:
        member = tar.getmembers()[0]
        extracted_file = tar.extractfile(member)
        if not extracted_file:
            raise FileNotFoundError(f"Could not extract {local_lib_path.name} from container archive.")
        with open(local_lib_path, 'wb') as f:
            f.write(extracted_file.read())
            
    container.remove()
    
    return local_lib_path, final_target
