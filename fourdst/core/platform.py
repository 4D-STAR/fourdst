# fourdst/core/platform.py

import json
import platform
import shutil
import subprocess
from pathlib import Path

from fourdst.core.config import ABI_CACHE_FILE, CACHE_PATH
from fourdst.core.utils import run_command

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

def _detect_and_cache_abi() -> dict:
    """
    Compiles and runs a C++ program to detect the compiler ABI, then caches it.
    Falls back to platform-based detection if meson is not available (e.g., in packaged apps).
    """
    import sys
    import logging
    
    # Use logging instead of print to avoid stdout contamination
    logger = logging.getLogger(__name__)
    logger.info("Performing one-time native C++ ABI detection...")
    
    # Check if meson is available
    meson_available = shutil.which("meson") is not None
    
    if not meson_available:
        logger.warning("Meson not available, using fallback platform detection")
        return _fallback_platform_detection()
    
    temp_dir = CACHE_PATH / "abi_detector"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    try:
        (temp_dir / "main.cpp").write_text(ABI_DETECTOR_CPP_SRC)
        (temp_dir / "meson.build").write_text(ABI_DETECTOR_MESON_SRC)

        logger.info("  - Configuring detector...")
        run_command(["meson", "setup", "build"], cwd=temp_dir)
        logger.info("  - Compiling detector...")
        run_command(["meson", "compile", "-C", "build"], cwd=temp_dir)

        detector_exe = temp_dir / "build" / "detector"
        logger.info("  - Running detector...")
        proc = subprocess.run([str(detector_exe)], check=True, capture_output=True, text=True)
        
        abi_details = {}
        for line in proc.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                abi_details[key] = value.strip()

        arch = platform.machine()
        stdlib_version = abi_details.get('stdlib_version', 'unknown')
        abi_string = f"{abi_details['compiler']}-{abi_details['stdlib']}-{stdlib_version}-{abi_details['abi']}"

        platform_data = {
            "os": abi_details['os'],
            "arch": arch,
            "triplet": f"{arch}-{abi_details['os']}",
            "abi_signature": abi_string,
            "details": abi_details,
            "is_native": True,
            "cross_file": None,
            "docker_image": None
        }

        with open(ABI_CACHE_FILE, 'w') as f:
            json.dump(platform_data, f, indent=4)
        
        logger.info(f"  - ABI details cached to {ABI_CACHE_FILE}")
        return platform_data

    except Exception as e:
        logger.warning(f"ABI detection failed: {e}, falling back to platform detection")
        return _fallback_platform_detection()
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def _fallback_platform_detection() -> dict:
    """
    Fallback platform detection that doesn't require external tools.
    Used when meson is not available (e.g., in packaged applications).
    """
    import sys
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("Using fallback platform detection (no external tools required)")
    
    # Get basic platform information
    arch = platform.machine()
    system = platform.system().lower()
    
    # Map common architectures
    arch_mapping = {
        'x86_64': 'x86_64',
        'AMD64': 'x86_64',
        'arm64': 'aarch64',
        'aarch64': 'aarch64',
        'i386': 'i686',
        'i686': 'i686'
    }
    normalized_arch = arch_mapping.get(arch, arch)
    
    # Detect compiler and stdlib based on platform
    if system == 'darwin':
        # macOS
        os_name = 'darwin'
        compiler = 'clang'
        stdlib = 'libc++'
        # Get macOS version for stdlib version
        mac_version = platform.mac_ver()[0]
        stdlib_version = mac_version.split('.')[0] if mac_version else 'unknown'
        abi = 'cxx11'
    elif system == 'linux':
        # Linux
        os_name = 'linux'
        # Try to detect if we're using GCC or Clang
        compiler = 'gcc'  # Default assumption
        stdlib = 'libstdc++'
        stdlib_version = '11'  # Common default
        abi = 'cxx11'
    elif system == 'windows':
        # Windows
        os_name = 'windows'
        compiler = 'msvc'
        stdlib = 'msvcrt'
        stdlib_version = 'unknown'
        abi = 'cxx11'
    else:
        # Unknown system
        os_name = system
        compiler = 'unknown'
        stdlib = 'unknown'
        stdlib_version = 'unknown'
        abi = 'unknown'
    
    abi_string = f"{compiler}-{stdlib}-{stdlib_version}-{abi}"
    
    platform_data = {
        "os": os_name,
        "arch": normalized_arch,
        "triplet": f"{normalized_arch}-{os_name}",
        "abi_signature": abi_string,
        "details": {
            "compiler": compiler,
            "stdlib": stdlib,
            "stdlib_version": stdlib_version,
            "abi": abi,
            "os": os_name,
            "detection_method": "fallback"
        },
        "is_native": True,
        "cross_file": None,
        "docker_image": None
    }
    
    # Cache the result
    try:
        CACHE_PATH.mkdir(parents=True, exist_ok=True)
        with open(ABI_CACHE_FILE, 'w') as f:
            json.dump(platform_data, f, indent=4)
        logger.info(f"Fallback platform data cached to {ABI_CACHE_FILE}")
    except Exception as e:
        logger.warning(f"Failed to cache platform data: {e}")
    
    return platform_data


def get_platform_identifier() -> dict:
    """
    Gets the native platform identifier, using a cached value if available.
    """
    if ABI_CACHE_FILE.exists():
        with open(ABI_CACHE_FILE, 'r') as f:
            plat = json.load(f)
    else:
        plat = _detect_and_cache_abi()
    plat['type'] = 'native'
    return plat

def _parse_version(version_str: str) -> tuple:
    """Parses a version string like '12.3.1' into a tuple of integers."""
    return tuple(map(int, (version_str.split('.') + ['0', '0'])[:3]))

def is_abi_compatible(host_platform: dict, binary_platform: dict) -> tuple[bool, str]:
    """
    Checks if a binary's platform is compatible with the host's platform.
    This is more nuanced than a simple string comparison, allowing for forward compatibility.
    - macOS: A binary for an older OS version can run on a newer one, if the toolchain matches.
    - Linux: A binary for an older GLIBC version can run on a newer one.
    """
    required_keys = ['os', 'arch', 'abi_signature']
    if not all(key in host_platform for key in required_keys):
        return False, f"Host platform data is malformed. Missing keys: {[k for k in required_keys if k not in host_platform]}"
    if not all(key in binary_platform for key in required_keys):
        return False, f"Binary platform data is malformed. Missing keys: {[k for k in required_keys if k not in binary_platform]}"

    host_os = host_platform.get('os') or host_platform.get('details', {}).get('os')
    binary_os = binary_platform.get('os') or binary_platform.get('details', {}).get('os')
    host_arch = host_platform.get('arch') or host_platform.get('details', {}).get('arch')
    binary_arch = binary_platform.get('arch') or binary_platform.get('details', {}).get('arch')

    if host_os != binary_os:
        return False, f"OS mismatch: host is {host_os}, binary is {binary_os}"
    if host_arch != binary_arch:
        return False, f"Architecture mismatch: host is {host_arch}, binary is {binary_arch}"

    host_sig = host_platform['abi_signature']
    binary_sig = binary_platform['abi_signature']

    try:
        host_parts = host_sig.split('-')
        binary_parts = binary_sig.split('-')

        # Find version numbers in any position
        host_ver_str = next((p for p in host_parts if p[0].isdigit()), None)
        binary_ver_str = next((p for p in binary_parts if p[0].isdigit()), None)

        if not host_ver_str or not binary_ver_str:
            return False, "Could not extract version from ABI signature"

        host_ver = _parse_version(host_ver_str)
        binary_ver = _parse_version(binary_ver_str)

        if host_platform['os'] == 'macos':
            # For macOS, also check for clang and libc++
            if 'clang' not in binary_sig:
                return False, "Toolchain mismatch: 'clang' not in binary signature"
            if 'libc++' not in binary_sig:
                return False, "Toolchain mismatch: 'libc++' not in binary signature"
            if host_ver < binary_ver:
                return False, f"macOS version too old: host is {host_ver_str}, binary needs {binary_ver_str}"
            return True, "Compatible"

        elif host_platform['os'] == 'linux':
            if host_ver < binary_ver:
                return False, f"GLIBC version too old: host is {host_ver_str}, binary needs {binary_ver_str}"
            return True, "Compatible"

    except (IndexError, ValueError, StopIteration):
        return False, "Malformed ABI signature string"

    return False, "Unknown compatibility check failure"

def get_macos_targeted_platform_identifier(target_version: str) -> dict:
    """
    Generates a platform identifier for a specific target macOS version.
    """
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
            "stdlib_version": target_version,
            "abi": abi,
        },
        "is_native": True,
        "cross_file": None,
        "docker_image": None,
        "arch": arch
    }
