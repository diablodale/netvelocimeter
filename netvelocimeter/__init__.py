"""NetVelocimeter - A Python library for measuring network performance.

This library provides a unified interface for measuring network performance metrics
such as bandwidth, latency, and ping times using various service providers.
"""

from .core import (
    MeasurementResult,
    NetVelocimeter,
    get_provider,
    library_version,
    list_providers,
    register_provider,
)
from .exceptions import LegalAcceptanceError, MeasurementError, PlatformNotSupported
from .legal import (
    LegalTerms,
    LegalTermsCategory,
    LegalTermsCategoryCollection,
    LegalTermsCollection,
)
from .providers.base import BaseProvider
from .providers.provider_info import ProviderInfo
from .providers.server_info import ServerInfo
from .utils.rates import DataRateMbps, Percentage, TimeDuration

# Dynamic version import
__version__: str
try:
    from importlib.metadata import version as _version

    __version__ = _version("netvelocimeter")
except (ImportError, ModuleNotFoundError):
    # Fallback for development environments where the library package itself is not installed
    __version__ = "0.9.8.dev7+654321abcdef"


# Dynamically import all provider modules which leads to them being registered
def _import_providers() -> None:
    """Import all provider modules from the providers directory."""
    import importlib
    import pathlib
    import pkgutil

    # Get the path to the current directory
    providers_dir = pathlib.Path(__file__).parent / "providers"

    # Import all Python files in this directory
    for module_info in pkgutil.iter_modules([str(providers_dir)]):
        # Skip __init__ and base modules
        if module_info.name not in ["__init__", "base"]:
            # Import the provider module
            importlib.import_module(f".{module_info.name}", package="netvelocimeter.providers")


# Run dynamic imports
_import_providers()

# Clean namespace
del _import_providers

# module names that are exposed to wildcard imports `from netvelocimeter import *`
__all__ = [
    "__version__",
    "MeasurementResult",
    "NetVelocimeter",
    "get_provider",
    "library_version",
    "list_providers",
    "register_provider",
    "LegalAcceptanceError",
    "MeasurementError",
    "PlatformNotSupported",
    "LegalTerms",
    "LegalTermsCategory",
    "LegalTermsCategoryCollection",
    "LegalTermsCollection",
    "BaseProvider",
    "ProviderInfo",
    "ServerInfo",
    "DataRateMbps",
    "Percentage",
    "TimeDuration",
]
