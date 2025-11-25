"""
Composition-module bindings
"""
from __future__ import annotations
import fourdst.atomic
import typing
from . import utils
__all__: list[str] = ['CanonicalComposition', 'Composition', 'utils']
class CanonicalComposition:
    def __repr__(self) -> str:
        ...
    @property
    def X(self) -> float:
        ...
    @property
    def Y(self) -> float:
        ...
    @property
    def Z(self) -> float:
        ...
class Composition:
    def __eq__(self, arg0: Composition) -> bool:
        ...
    def __hash__(self) -> int:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, symbols: list[str]) -> None:
        """
        Constructor taking a list of symbols to register
        """
    @typing.overload
    def __init__(self, symbols: set[str]) -> None:
        """
        Constructor taking a set of symbols to register
        """
    @typing.overload
    def __init__(self, species: list[fourdst.atomic.Species]) -> None:
        """
        Constructor taking a list of species to register
        """
    @typing.overload
    def __init__(self, species: set[fourdst.atomic.Species]) -> None:
        """
        Constructor taking a set of species to register
        """
    @typing.overload
    def __init__(self, symbols: list[str], molarAbundances: list[float]) -> None:
        """
        Constructor taking a list of symbols and molar abundances
        """
    @typing.overload
    def __init__(self, species: list[fourdst.atomic.Species], molarAbundances: list[float]) -> None:
        """
        Constructor taking a list of species and molar abundances
        """
    @typing.overload
    def __init__(self, symbols: set[str], molarAbundances: list[float]) -> None:
        """
        Constructor taking a set of symbols and a list of molar abundances
        """
    @typing.overload
    def __init__(self, speciesMolarAbundances: dict[fourdst.atomic.Species, float]) -> None:
        """
        Constructor taking an unordered map of species to molar abundances
        """
    @typing.overload
    def __init__(self, speciesMolarAbundances: dict[fourdst.atomic.Species, float]) -> None:
        """
        Constructor taking a map of species to molar abundances
        """
    def __iter__(self) -> typing.Iterator[tuple[fourdst.atomic.Species, float]]:
        ...
    def __repr__(self) -> str:
        ...
    @typing.overload
    def contains(self, symbol: str) -> bool:
        """
        Check if a symbol is in the composition.
        """
    @typing.overload
    def contains(self, species: fourdst.atomic.Species) -> bool:
        """
        Check if a species is in the composition.
        """
    def getCanonicalComposition(self) -> CanonicalComposition:
        """
        Get a canonical composition (X, Y, Z). d
        """
    @typing.overload
    def getMassFraction(self, symbol: str) -> float:
        """
        Get mass fraction for a symbol.
        """
    @typing.overload
    def getMassFraction(self, species: fourdst.atomic.Species) -> float:
        """
        Get mass fraction for a species.
        """
    @typing.overload
    def getMassFraction(self) -> dict[fourdst.atomic.Species, float]:
        """
        Get dictionary of all mass fractions. 
        """
    def getMassFractionVector(self) -> list[float]:
        """
        Get mass fractions as a vector (ordered by species mass).
        """
    def getMeanParticleMass(self) -> float:
        """
        Get the mean particle mass (amu)
        """
    @typing.overload
    def getMolarAbundance(self, symbol: str) -> float:
        """
        Get molar abundance for a symbol.
        """
    @typing.overload
    def getMolarAbundance(self, species: fourdst.atomic.Species) -> float:
        """
        Get molar abundance for a species.
        """
    def getMolarAbundanceVector(self) -> list[float]:
        """
        Get molar abundances as a vector (ordered by species mass).
        """
    @typing.overload
    def getNumberFraction(self, symbol: str) -> float:
        """
        Get number fraction for a symbol.
        """
    @typing.overload
    def getNumberFraction(self, species: fourdst.atomic.Species) -> float:
        """
        Get number fraction for a species.
        """
    @typing.overload
    def getNumberFraction(self) -> dict[fourdst.atomic.Species, float]:
        """
        Get dictionary of all number fractions.
        """
    def getNumberFractionVector(self) -> list[float]:
        """
        Get number fractions as a vector (ordered by species mass)
        """
    def getRegisteredSpecies(self) -> set[fourdst.atomic.Species]:
        """
        Get the set of registered species.
        """
    def getRegisteredSymbols(self) -> set[str]:
        """
        Get the set of registered symbols.
        """
    def getSpeciesAtIndex(self, index: int) -> fourdst.atomic.Species:
        """
        Get the species at a given index in the internal ordering.
        """
    @typing.overload
    def getSpeciesIndex(self, symbol: str) -> int:
        """
        Get the index of a species in the internal ordering.
        """
    @typing.overload
    def getSpeciesIndex(self, species: fourdst.atomic.Species) -> int:
        """
        Get the index of a species in the internal ordering.
        """
    @typing.overload
    def registerSpecies(self, species: fourdst.atomic.Species) -> None:
        """
        Register a single species. The molar abundance will be initialized to zero.
        """
    @typing.overload
    def registerSpecies(self, species: list[fourdst.atomic.Species]) -> None:
        """
        Register multiple species. Each molar abundance will be initialized to zero.
        """
    @typing.overload
    def registerSymbol(self, symbol: str) -> None:
        """
        Register a single symbol. The molar abundance will be initialized to zero.
        """
    @typing.overload
    def registerSymbol(self, symbols: list[str]) -> None:
        """
        Register multiple symbols. Each molar abundance will be initialized to zero.
        """
    @typing.overload
    def setMolarAbundance(self, symbol: str, molarAbundance: float) -> None:
        """
        Set the molar abundance for a symbol.
        """
    @typing.overload
    def setMolarAbundance(self, species: fourdst.atomic.Species, molarAbundance: float) -> None:
        """
        Set the molar abundance for a species.
        """
    @typing.overload
    def setMolarAbundance(self, symbols: list[str], molarAbundances: list[float]) -> None:
        """
        Set the molar abundance for a list of symbols. The molar abundance vector must be parallel to the symbols vector.
        """
    @typing.overload
    def setMolarAbundance(self, species: list[fourdst.atomic.Species], molarAbundances: list[float]) -> None:
        """
        Set the molar abundance for a list of species. The molar abundance vector must be parallel to the species vector.
        """
    def size(self) -> int:
        """
        Get the number of registered species in the composition.
        """
