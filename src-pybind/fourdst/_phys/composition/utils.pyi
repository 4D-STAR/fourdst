"""
Utility functions for Composition
"""
from __future__ import annotations
import fourdst.atomic
import fourdst.composition
import typing
__all__: list[str] = ['CompositionHash', 'buildCompositionFromMassFractions']
class CompositionHash:
    @staticmethod
    def hash_exact(composition: fourdst.composition.Composition) -> int:
        """
        Compute a hash for a given Composition object.
        """
    @staticmethod
    def hash_quantized(composition: fourdst.composition.Composition, eps: float) -> int:
        """
        Compute a quantized hash for a given Composition object with specified precision.
        """
@typing.overload
def buildCompositionFromMassFractions(symbols: list[str], massFractions: list[float]) -> fourdst.composition.Composition:
    """
    Build a Composition object from symbols and their corresponding mass fractions.
    """
@typing.overload
def buildCompositionFromMassFractions(species: list[fourdst.atomic.Species], massFractions: list[float]) -> fourdst.composition.Composition:
    """
    Build a Composition object from species and their corresponding mass fractions.
    """
@typing.overload
def buildCompositionFromMassFractions(species: set[fourdst.atomic.Species], massFractions: list[float]) -> fourdst.composition.Composition:
    """
    Build a Composition object from species in a set and their corresponding mass fractions.
    """
@typing.overload
def buildCompositionFromMassFractions(massFractionsMap: dict[fourdst.atomic.Species, float]) -> fourdst.composition.Composition:
    """
    Build a Composition object from a map of species to mass fractions.
    """
@typing.overload
def buildCompositionFromMassFractions(massFractionsMap: dict[fourdst.atomic.Species, float]) -> fourdst.composition.Composition:
    """
    Build a Composition object from a map of species to mass fractions.
    """
