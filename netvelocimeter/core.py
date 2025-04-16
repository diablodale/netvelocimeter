"""
Core functionality for the NetVelocimeter library.
"""

import os
import importlib
from typing import Dict, Optional, Type, List, Union
from packaging.version import Version

from .providers.base import BaseProvider, ProviderLegalRequirements, MeasurementResult, ServerInfo
from .exceptions import LegalAcceptanceError


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
        binary_dir: Optional[str] = None,
        accept_eula: bool = False,
        accept_terms: bool = False,
        accept_privacy: bool = False
    ):
        """
        Initialize the NetVelocimeter.

        Args:
            provider: The name of the provider to use.
            binary_dir: Directory to store provider binaries.
            accept_eula: Whether to accept the provider's EULA.
            accept_terms: Whether to accept the provider's terms of service.
            accept_privacy: Whether to accept the provider's privacy policy.
        """
        provider_class = get_provider(provider)

        if binary_dir is None:
            binary_dir = os.path.expanduser("~/.netvelocimeter/bin/")
            os.makedirs(binary_dir, exist_ok=True)

        self.provider = provider_class(binary_dir)
        self._accepted_eula = accept_eula
        self._accepted_terms = accept_terms
        self._accepted_privacy = accept_privacy

        # Store acceptance status in the provider
        if hasattr(self.provider, "_accepted_eula"):
            self.provider._accepted_eula = accept_eula
        if hasattr(self.provider, "_accepted_terms"):
            self.provider._accepted_terms = accept_terms
        if hasattr(self.provider, "_accepted_privacy"):
            self.provider._accepted_privacy = accept_privacy

    def check_legal_requirements(self) -> bool:
        """
        Check if all legal requirements are satisfied.

        Returns:
            True if all requirements are met, False otherwise
        """
        return self.provider.check_acceptance(
            accepted_eula=self._accepted_eula,
            accepted_terms=self._accepted_terms,
            accepted_privacy=self._accepted_privacy
        )

    def get_legal_requirements(self) -> ProviderLegalRequirements:
        """
        Get legal requirements for the current provider.

        Returns:
            A ProviderLegalRequirements object
        """
        return self.provider.legal_requirements

    def get_servers(self) -> List[ServerInfo]:
        """
        Get list of available servers.

        Returns:
            List of server information objects.
        """
        return self.provider.get_servers()

    def get_provider_version(self) -> Version:
        """
        Get the version of the provider.

        Returns:
            Provider version as a Version object.
        """
        return self.provider.version

    def measure(self, server_id: Optional[Union[int, str]] = None, server_host: Optional[str] = None) -> MeasurementResult:
        """
        Measure network performance using the configured provider.

        Args:
            server_id: Server ID to use for testing (either integer or string)
            server_host: Server hostname to use for testing

        Returns:
            Measurement results
        """
        if not self.check_legal_requirements():
            legal = self.get_legal_requirements()
            raise LegalAcceptanceError(
                "You must accept the legal requirements before running tests.\n"
                f"EULA: {legal.eula_url}\n"
                f"Terms of Service: {legal.terms_url}\n"
                f"Privacy Policy: {legal.privacy_url}"
            )

        return self.provider.measure(server_id=server_id, server_host=server_host)

    def measure_download(self):
        """Measure download speed."""
        return self.provider.measure_download()

    def measure_upload(self):
        """Measure upload speed."""
        return self.provider.measure_upload()

    def measure_latency(self):
        """Measure network latency."""
        return self.provider.measure_latency()
