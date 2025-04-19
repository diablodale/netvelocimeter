"""
Static provider usually used for testing.
"""

from datetime import timedelta
import re

from packaging.version import Version

from ..core import register_provider
from .base import (
    BaseProvider,
    MeasurementResult,
    ProviderLegalRequirements,
    ServerIDType,
    ServerInfo,
)


class StaticProvider(BaseProvider):
    """
    Configurable test provider that can be used across test cases.
    All fields default to test values, set any to None to omit them.
    Five test servers with ids 1 -> 5 are available.
    """

    def __init__(self,
                 binary_dir: str,
                 requires_acceptance: bool = True,
                 eula_text: str | None = "Test EULA",
                 eula_url: str | None = "https://example.com/eula",
                 terms_text: str | None = "Test Terms",
                 terms_url: str | None = "https://example.com/terms",
                 privacy_text: str | None = "Test Privacy",
                 privacy_url: str | None = "https://example.com/privacy",
                 download_speed: float = 100.0,
                 upload_speed: float = 50.0,
                 download_latency: timedelta = timedelta(milliseconds=30.0),
                 upload_latency: timedelta = timedelta(milliseconds=60.0),
                 ping_latency: timedelta = timedelta(milliseconds=25.0),
                 ping_jitter: timedelta = timedelta(milliseconds=20.0),
                 packet_loss: float = 1.3,
                 version: str = "1.2.3+c0ffee",
                 accepted_eula: bool = False,
                 accepted_terms: bool = False,
                 accepted_privacy: bool = False):
        """
        Initialize a configurable test provider.

        Args:
            binary_dir: Directory for binaries
            requires_acceptance: Whether legal acceptance is required
            eula_text: EULA text (None to omit)
            eula_url: EULA URL (None to omit)
            terms_text: Terms text (None to omit)
            terms_url: Terms URL (None to omit)
            privacy_text: Privacy text (None to omit)
            privacy_url: Privacy URL (None to omit)
            download_speed: Download speed to return in test results (Mbps)
            upload_speed: Upload speed to return in test results (Mbps)
            download_latency: Download latency to return in test results (ms)
            upload_latency: Upload latency to return in test results (ms)
            ping_latency: Ping latency to return in test results (ms)
            ping_jitter: Ping jitter to return in test results (ms)
            packet_loss: Packet loss percentage to return in test results
            version: Provider version string
            accepted_eula: Whether EULA is accepted
            accepted_terms: Whether Terms are accepted
            accepted_privacy: Whether Privacy policy is accepted
        """
        super().__init__(binary_dir)
        self.version = Version(version)
        self._requires_acceptance = requires_acceptance
        self._eula_text = eula_text
        self._eula_url = eula_url
        self._terms_text = terms_text
        self._terms_url = terms_url
        self._privacy_text = privacy_text
        self._privacy_url = privacy_url
        self._download_speed = download_speed
        self._upload_speed = upload_speed
        self._download_latency = download_latency
        self._upload_latency = upload_latency
        self._ping_latency = ping_latency
        self._ping_jitter = ping_jitter
        self._packet_loss = packet_loss
        self._version = version
        self._accepted_eula = accepted_eula
        self._accepted_terms = accepted_terms
        self._accepted_privacy = accepted_privacy

    @property
    def legal_requirements(self) -> ProviderLegalRequirements:
        """Get the provider's legal requirements."""
        return ProviderLegalRequirements(
            eula_text=self._eula_text,
            eula_url=self._eula_url,
            terms_text=self._terms_text,
            terms_url=self._terms_url,
            privacy_text=self._privacy_text,
            privacy_url=self._privacy_url,
            requires_acceptance=self._requires_acceptance
        )

    def _generate_server_info(self, server_num: int) -> ServerInfo:
        """Generate a test server info object with the given server number."""
        return ServerInfo(
            name=f"Test Server {server_num}",
            id=server_num,
            host=f"test{server_num}.example.com",
            location=f"Test Location {server_num}",
            country="Test Country"
        )

    def get_servers(self) -> list[ServerInfo]:
        """Get list of available servers."""
        return [
            self._generate_server_info(i) for i in range(1, 6)
        ]

    def measure(self, server_id: ServerIDType | None = None, server_host: str | None = None) -> MeasurementResult:
        """
        Measure network speed with the specified parameters.

        Args:
            server_id: ID of the server to use (1-5)
            server_host: Hostname of the server to use

        Returns:
            Measurement results

        Raises:
            ValueError: If server_id or server_host is invalid
        """
        # Check that server_id or server_host is within the list of servers. Either
        # * server_id can be coerced to an int between 1 -> 5
        # * server_host is one of the known test servers
        if server_id:
            server_num = int(server_id)
            if not (1 <= server_num <= 5):
                raise ValueError("server_id must be between 1 and 5")
        elif server_host:
            # Extract server number from host string
            match = re.match(r"^test([1-5])\.example\.com$", server_host)
            if not match:
                raise ValueError("server_host must be testX.example.com where X is between 1 and 5")
            server_num = int(match.group(1))
        else:
            server_num = 1

        # Return a test measurement result
        return MeasurementResult(
            download_speed=self._download_speed,
            upload_speed=self._upload_speed,
            download_latency=self._download_latency,
            upload_latency=self._upload_latency,
            ping_latency=self._ping_latency,
            ping_jitter=self._ping_jitter,
            packet_loss=self._packet_loss,
            server_info=self._generate_server_info(server_num),
            persist_url="https://example.com/results/static-test-1234",
            id=f"static-test-{server_num}-{hash(self)}"
        )

# Register this provider
register_provider("static", StaticProvider)
