"""Base class for all speed test providers."""

from abc import ABC, abstractmethod
from typing import final

from packaging.version import Version

from ..legal import (
    AcceptanceTracker,
    LegalTerms,
    LegalTermsCategory,
    LegalTermsCategoryCollection,
    LegalTermsCollection,
)
from .measurement_result import MeasurementResult
from .server_info import ServerIDType, ServerInfo


class BaseProvider(ABC):
    """Base class for network performance measurement providers."""

    def __init__(self, *, config_root: str | None = None) -> None:
        r"""Initialize the provider.

        Args:
            config_root: Directory to store configuration, e.g. legal acceptance
                - None: Use default location (%%APPDATA%%\netvelocimeter or ~/.config/netvelocimeter)
                - str: Custom directory path
        """
        self._acceptance = AcceptanceTracker(config_root=config_root)

    @property
    @abstractmethod
    def _version(self) -> Version:
        """Get the provider version.

        Each provider type must implement this property to return
        its specific version.

        Returns:
            The version of the provider implementation
        """
        pass  # pragma: no cover

    @abstractmethod
    def _legal_terms(
        self, categories: LegalTermsCategory | LegalTermsCategoryCollection = LegalTermsCategory.ALL
    ) -> LegalTermsCollection:
        """Get legal terms for this provider.

        Args:
            categories: Category(s) of terms to retrieve. Defaults to ALL.

        Returns:
            Collection of legal terms that match the requested category
        """
        pass  # pragma: no cover

    @abstractmethod
    def _measure(
        self, server_id: ServerIDType | None = None, server_host: str | None = None
    ) -> MeasurementResult:
        """Measure network performance.

        Args:
            server_id: Server ID to use for testing (either integer or string)
            server_host: Server hostname to use for testing

        Returns:
            Measurement results
        """
        pass  # pragma: no cover

    @property
    def _servers(self) -> list[ServerInfo]:
        """Get a list of available servers.

        Returns:
            List of server information objects.
        """
        raise NotImplementedError("This provider does not support listing servers")

    @final
    def _has_accepted_terms(
        self, terms_or_collection: LegalTerms | LegalTermsCollection | None = None
    ) -> bool:
        """Check if the user has accepted the specified terms.

        Args:
            terms_or_collection: Terms to check. If None, checks all legal terms for this provider.

        Returns:
            True if all specified terms have been accepted, False otherwise
        """
        if terms_or_collection is None:
            terms_or_collection = self._legal_terms()

        return self._acceptance.is_recorded(terms_or_collection)

    @final
    def _accept_terms(self, terms_or_collection: LegalTerms | LegalTermsCollection) -> None:
        """Record acceptance of terms.

        Args:
            terms_or_collection: Terms to accept

        Raises:
            TypeError: If the input is not a LegalTerms or LegalTermsCollection
            OSError: If the acceptance cannot be recorded
        """
        self._acceptance.record(terms_or_collection)
