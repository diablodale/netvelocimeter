"""
Base class for all speed test providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from packaging.version import Version

# type alias for server ID
ServerIDType = int | str

@dataclass
class ProviderLegalRequirements:
    """Defines legal requirements for a network provider.

    Attributes:
        eula_text: Text of the End User License Agreement (EULA).
        eula_url: URL to the EULA.
        terms_text: Text of the Terms of Service.
        terms_url: URL to the Terms of Service.
        privacy_text: Text of the Privacy Policy.
        privacy_url: URL to the Privacy Policy.
        requires_acceptance: Whether acceptance of legal documents is required.
    """

    eula_text: str | None = None
    eula_url: str | None = None
    terms_text: str | None = None
    terms_url: str | None = None
    privacy_text: str | None = None
    privacy_url: str | None = None
    requires_acceptance: bool = False


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
        """require name to be set"""
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
    upload_speed: float    # in Mbps
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

    binary_dir: str # TODO change to Path
    version: Version

    def __init__(self, binary_dir: str):
        """
        Initialize the provider.

        Args:
            binary_dir: Directory to store provider binaries.
        """
        self.binary_dir = binary_dir
        self.version = Version("0")

    @property
    def legal_requirements(self) -> ProviderLegalRequirements:
        """Get legal requirements for this provider."""
        # Default implementation returns no requirements
        return ProviderLegalRequirements(requires_acceptance=False)

    @abstractmethod
    def measure(self, server_id: ServerIDType | None = None, server_host: str | None = None) -> MeasurementResult:
        """
        Measure network performance.

        Args:
            server_id: Server ID to use for testing (either integer or string)
            server_host: Server hostname to use for testing

        Returns:
            Measurement results
        """
        pass

    def check_acceptance(self,
                        accepted_eula: bool = False,
                        accepted_terms: bool = False,
                        accepted_privacy: bool = False) -> bool:
        """
        Check if user has accepted required legal documents.

        Args:
            accepted_eula: Whether the user has accepted the EULA
            accepted_terms: Whether the user has accepted the terms of service
            accepted_privacy: Whether the user has accepted the privacy policy

        Returns:
            True if all requirements are met, False otherwise
        """
        legal = self.legal_requirements
        if not legal.requires_acceptance:
            return True

        if (legal.eula_text or legal.eula_url) and not accepted_eula:
            return False

        if (legal.terms_text or legal.terms_url) and not accepted_terms:
            return False

        if (legal.privacy_text or legal.privacy_url) and not accepted_privacy:
            return False

        return True

    def get_servers(self) -> list[ServerInfo]:
        """
        Get a list of available servers.

        Returns:
            List of server information objects.
        """
        raise NotImplementedError("This provider does not support listing servers")

    def get_version(self) -> Version:
        """
        Get the version of the provider tool.

        Returns:
            Version string of the provider tool.
        """
        return self.version
