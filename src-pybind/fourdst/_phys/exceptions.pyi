"""
Exception bindings
"""
from __future__ import annotations
__all__: list[str] = ['CompositionError', 'InvalidCompositionError', 'SpeciesError', 'UnknownSymbolError', 'UnregisteredSymbolError']
class CompositionError(Exception):
    pass
class InvalidCompositionError(CompositionError):
    pass
class SpeciesError(Exception):
    pass
class UnknownSymbolError(SpeciesError):
    pass
class UnregisteredSymbolError(SpeciesError):
    pass
