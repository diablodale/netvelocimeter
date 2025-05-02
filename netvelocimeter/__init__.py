"""NetVelocimeter - A Python library for measuring network performance.

This library provides a unified interface for measuring network performance metrics
such as bandwidth, latency, and ping times using various service providers.
"""

from .core import NetVelocimeter, get_provider, list_providers, register_provider

# Dynamic version import
try:
    from importlib.metadata import version as _version

    __version__ = _version("netvelocimeter")
except (ImportError, ModuleNotFoundError):
    # Fallback for development environments where the library package itself is not installed
    __version__ = "0.9.8.dev7+654321abcdef"

# module names that are exposed to wildcard imports `from netvelocimeter import *`
__all__ = ["NetVelocimeter", "get_provider", "list_providers", "register_provider"]
