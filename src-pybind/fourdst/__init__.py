# src-pybind/fourdst/__init__.py
from __future__ import annotations
import sys

from ._phys import atomic, composition, constants, config

sys.modules['fourdst.atomic'] = atomic
sys.modules['fourdst.composition'] = composition
sys.modules['fourdst.constants'] = constants
sys.modules['fourdst.config'] = config

__all__ = ['atomic', 'composition', 'constants', 'config', 'core', 'cli']

__version__ = 'v0.9.11'