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