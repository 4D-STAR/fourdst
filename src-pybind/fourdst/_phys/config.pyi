"""
Configuration-module bindings
"""
from __future__ import annotations
import typing
__all__: list[str] = ['get', 'has', 'keys', 'loadConfig']
def __repr__() -> str:
    ...
@typing.overload
def get(key: str, defaultValue: int) -> int:
    """
    Get configuration value (type inferred from default)
    """
@typing.overload
def get(key: str, defaultValue: float) -> float:
    """
    Get configuration value (type inferred from default)
    """
@typing.overload
def get(key: str, defaultValue: str) -> str:
    """
    Get configuration value (type inferred from default)
    """
@typing.overload
def get(key: str, defaultValue: bool) -> bool:
    """
    Get configuration value (type inferred from default)
    """
def has(key: str) -> bool:
    """
    Check if a key exists in the configuration.
    """
def keys() -> typing.Any:
    """
    Get a list of all configuration keys.
    """
def loadConfig(configFilePath: str) -> bool:
    """
    Load configuration from a YAML file.
    """
