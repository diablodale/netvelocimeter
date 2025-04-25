"""Base class for all speed test providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, final

from packaging.version import Version

from ..terms import AcceptanceTracker, LegalTerms, LegalTermsCategory, LegalTermsCollection

# type alias for server ID
ServerIDType = int | str


@dataclass
class ServerInfo:
    """Information about a speed test server.

    Attributes:
        name: Descriptive name of the server.
        id: Server ID (can be int or str).
        location: Location name of the server.
        country: Country name of the server.
        host: Hostname or IP address of the server.
        raw_server: Raw provider-specific server data.
    """

    name: str
    id: ServerIDType | None = None
    location: str | None = None
    country: str | None = None
    host: str | None = None
    raw_server: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Require name to be set."""
        if not self.name:
            raise ValueError("Name cannot be empty")

    def __str__(self) -> str:
        """Return a string representation of the server info."""
        parts = []
        if self.id is None:
            parts.append(f"Server: {self.name}")
        else:
            parts.append(f"Server: {self.name} ({self.id})")
        if self.location:
            parts.append(f"Location: {self.location}")
        if self.country:
            parts.append(f"Country: {self.country}")
        if self.host:
            parts.append(f"Host: {self.host}")
        return ", ".join(parts)


@dataclass
class MeasurementResult:
    """Result of a network measurement.

    Attributes:
        download_speed: Download speed in Mbps (megabits per second).
        upload_speed: Upload speed in Mbps.
        download_latency: Download latency as timedelta.
        upload_latency: Upload latency as timedelta.
        ping_latency: Ping latency as timedelta.
        ping_jitter: Ping jitter as timedelta.
        packet_loss: Packet loss percentage.
        server_info: Information about the server used for testing.
        persist_url: URL to view test results.
        id: Provider-assigned measurement ID.
        raw_result: Raw provider result data.
    """

    download_speed: float  # in Mbps
    upload_speed: float  # in Mbps
    download_latency: timedelta | None = None
    upload_latency: timedelta | None = None
    ping_latency: timedelta | None = None
    ping_jitter: timedelta | None = None
    packet_loss: float | None = None
    server_info: ServerInfo | None = None
    persist_url: str | None = None
    id: str | None = None
    raw_result: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Ensure download and upload speeds are set."""
        if self.download_speed is None or self.upload_speed is None:
            raise ValueError("Download and upload speeds must be provided")

    def __str__(self) -> str:
        """Return a string representation of the measurement result."""
        parts = []
        if self.download_speed is not None:
            parts.append(f"Download: {self.download_speed:.2f} Mbps")
        if self.upload_speed is not None:
            parts.append(f"Upload: {self.upload_speed:.2f} Mbps")
        if self.download_latency is not None:
            dl_latency_ms = self.download_latency.total_seconds() * 1000
            parts.append(f"Download Latency: {dl_latency_ms:.2f} ms")
        if self.upload_latency is not None:
            ul_latency_ms = self.upload_latency.total_seconds() * 1000
            parts.append(f"Upload Latency: {ul_latency_ms:.2f} ms")
        if self.ping_latency is not None:
            latency_ms = self.ping_latency.total_seconds() * 1000
            parts.append(f"Ping Latency: {latency_ms:.2f} ms")
        if self.ping_jitter is not None:
            jitter_ms = self.ping_jitter.total_seconds() * 1000
            parts.append(f"Ping Jitter: {jitter_ms:.2f} ms")
        if self.packet_loss is not None:
            parts.append(f"Packet Loss: {self.packet_loss:.2f}%")
        if self.id is not None:
            parts.append(f"ID: {self.id}")
        if self.persist_url is not None:
            parts.append(f"URL: {self.persist_url}")
        if self.server_info:
            parts.append(str(self.server_info))

        return ", ".join(parts)


class BaseProvider(ABC):
    """Base class for network performance measurement providers."""

    def __init__(self) -> None:
        """Initialize the provider."""
        self._acceptance = AcceptanceTracker()  # BUGBUG make attribute of derived class?

    @property
    @abstractmethod
    def version(self) -> Version:
        """Get the provider version.

        Each provider type must implement this property to return
        its specific version.

        Returns:
            The version of the provider implementation
        """
        pass

    @abstractmethod
    def legal_terms(
        self, category: LegalTermsCategory = LegalTermsCategory.ALL
    ) -> LegalTermsCollection:
        """Get legal terms for this provider.

        Args:
            category: Category of terms to retrieve. Defaults to ALL.

        Returns:
            Collection of legal terms that match the requested category
        """
        pass

    @abstractmethod
    def measure(
        self, server_id: ServerIDType | None = None, server_host: str | None = None
    ) -> MeasurementResult:
        """Measure network performance.

        Args:
            server_id: Server ID to use for testing (either integer or string)
            server_host: Server hostname to use for testing

        Returns:
            Measurement results
        """
        pass

    @property
    def servers(self) -> list[ServerInfo]:
        """Get a list of available servers.

        Returns:
            List of server information objects.
        """
        raise NotImplementedError("This provider does not support listing servers")

    @final
    def has_accepted_terms(
        self, terms_or_collection: LegalTerms | LegalTermsCollection | None = None
    ) -> bool:
        """Check if the user has accepted the specified terms.

        Args:
            terms_or_collection: Terms to check. If None, checks all legal terms for this provider.

        Returns:
            True if all specified terms have been accepted, False otherwise
        """
        if terms_or_collection is None:
            terms_or_collection = self.legal_terms()

        return self._acceptance.is_recorded(terms_or_collection)

    @final
    def accept_terms(self, terms_or_collection: LegalTerms | LegalTermsCollection) -> None:
        """Record acceptance of terms.

        Args:
            terms_or_collection: Terms to accept
        """
        self._acceptance.record(terms_or_collection)
