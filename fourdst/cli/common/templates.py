# fourdst/cli/common/templates.py

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
