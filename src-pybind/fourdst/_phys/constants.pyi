"""
Constants-module bindings
"""
from __future__ import annotations
import typing
__all__: list[str] = ['Constant', 'Constants']
class Constant:
    def __repr__(self) -> str:
        ...
    @property
    def name(self) -> str:
        ...
    @property
    def reference(self) -> str:
        ...
    @property
    def uncertainty(self) -> float:
        ...
    @property
    def unit(self) -> str:
        ...
    @property
    def value(self) -> float:
        ...
class Constants:
    @staticmethod
    def __class_getitem__(arg0: str) -> typing.Any:
        ...
    @staticmethod
    def get(arg0: str) -> typing.Any:
        """
        Get a constant by name. Returns None if not found.
        """
    @staticmethod
    def has(arg0: str) -> bool:
        """
        Check if a constant exists by name.
        """
    @staticmethod
    def keys() -> typing.Any:
        """
        Get a list of all constant names.
        """
    @property
    def loaded(self) -> bool:
        ...
