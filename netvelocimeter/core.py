"""
Core functionality for the NetVelocimeter library.
"""

import os
import importlib
from typing import Dict, Optional, Type, Union

from .providers.base import BaseProvider


_PROVIDERS: Dict[str, Type[BaseProvider]] = {}


def register_provider(name: str, provider_class: Type[BaseProvider]) -> None:
    """Register a provider with the library."""
    _PROVIDERS[name.lower()] = provider_class


def get_provider(name: str) -> Type[BaseProvider]:
    """Get a provider class by name."""
    if not _PROVIDERS:
        # Auto-import providers when first needed
        _discover_providers()

    name = name.lower()
    if name not in _PROVIDERS:
        raise ValueError(f"Provider '{name}' not found. Available providers: {', '.join(_PROVIDERS.keys())}")

    return _PROVIDERS[name]


def _discover_providers() -> None:
    """Automatically discover and register providers."""
    from .providers import ookla
    # Future providers will be imported here


class NetVelocimeter:
    """Main class for the NetVelocimeter library."""

    def __init__(
        self,
        provider: str = "ookla",
        binary_dir: Optional[str] = None
    ):
        """
        Initialize the NetVelocimeter.

        Args:
            provider: The name of the provider to use.
            binary_dir: Directory to store provider binaries.
                        If None, uses ~/.netvelocimeter/bin/
        """
        provider_class = get_provider(provider)

        if binary_dir is None:
            binary_dir = os.path.expanduser("~/.netvelocimeter/bin/")
            os.makedirs(binary_dir, exist_ok=True)

        self.provider = provider_class(binary_dir)

    def measure(self):
        """Measure network performance using the configured provider."""
        return self.provider.measure()

    def measure_download(self):
        """Measure download speed."""
        return self.provider.measure_download()

    def measure_upload(self):
        """Measure upload speed."""
        return self.provider.measure_upload()

    def measure_latency(self):
        """Measure network latency."""
        return self.provider.measure_latency()