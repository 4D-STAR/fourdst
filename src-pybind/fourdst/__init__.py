# src-pybind/fourdst/__init__.py
from __future__ import annotations
import sys

from ._phys import atomic, composition, constants, config
from ._phys.composition import utils, io

sys.modules['fourdst.atomic'] = atomic
sys.modules['fourdst.composition'] = composition
sys.modules['fourdst.constants'] = constants
sys.modules['fourdst.config'] = config
sys.modules['fourdst.composition.utils'] = utils
sys.modules['fourdst.composition.io'] = io

__all__ = ['atomic', 'composition', 'constants', 'config', 'core', 'cli']

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("fourdst")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

import os
from pathlib import Path
from typing import List

_PACKAGE_DIR = Path(__file__).resolve().parent

def get_lib_dirs() -> List[str]:
    return [
        os.fspath(_PACKAGE_DIR / "lib"),
        os.fspath(_PACKAGE_DIR / "lib" / "vendor"),
    ]

def get_include_dirs() -> List[str]:
    return [
        os.fspath(_PACKAGE_DIR / "include"),
        os.fspath(_PACKAGE_DIR / "include" / "fourdst" / "vendor"),
    ]

def get_rpath_flags() -> List[str]:
    return ["-Wl,-rpath," + os.fspath(_PACKAGE_DIR / "lib")]

def get_lib_flags() -> List[str]:
    flags = ["-L" + d for d in get_lib_dirs()]
    flags += ["-lcomposition", "-llogging", "-lconst", "-lreflect_cpp"]
    flags += get_rpath_flags()
    return flags

def get_include_flags() -> List[str]:
    return ["-I" + d for d in get_include_dirs()]

def get_compiler_flags() -> List[str]:
    return get_include_flags() + get_lib_flags()

def get_compiler_flags_formatted() -> int:
    flags = get_compiler_flags()
    print(' '.join(flags))
    return 0

def print_fourdst_version() -> int:
    print("fourdst version: " + __version__)
    return 0