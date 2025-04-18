"""
Static provider usually used for testing.
"""

from datetime import timedelta
from packaging.version import Version
from typing import Optional, Union

from ..core import register_provider
from netvelocimeter.providers.base import BaseProvider, MeasurementResult, ServerInfo, ProviderLegalRequirements

class StaticProvider(BaseProvider):
    """
    A configurable test provider that can be used across test cases.
    All fields default to test values, set any to None to omit them.
    Six test servers with ids 1 -> 5 are available.
    """

    def __init__(self,
                 binary_dir: str,
                 requires_acceptance: bool = True,
                 eula_text: Optional[str] = "Test EULA",
                 eula_url: Optional[str] = "https://example.com/eula",
                 terms_text: Optional[str] = "Test Terms",
                 terms_url: Optional[str] = "https://example.com/terms",
                 privacy_text: Optional[str] = "Test Privacy",
                 privacy_url: Optional[str] = "https://example.com/privacy",
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
            download_speed: Download speed to return in test results
            upload_speed: Upload speed to return in test results
            ping_latency: Ping latency to return in test results (ms)
            ping_jitter: Ping jitter to return in test results (ms)
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
        self._download_latency: timedelta = download_latency
        self._upload_latency: timedelta = upload_latency
        self._ping_latency: timedelta = ping_latency
        self._ping_jitter: timedelta = ping_jitter
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

    def _generate_server_info(self, server_id: Union[int, str]) -> ServerInfo:
        """Generate server info based on server ID."""
        return ServerInfo(
            id=server_id,
            name=f"Test Server {server_id}",
            host=f"test{server_id}.example.com",
            location="Test Location {server_id}",
            country="Test Country"
        )

    def get_servers(self):
        """Get list of available servers."""
        return [
            self._generate_server_info(i) for i in range(1, 6)
        ]

    def measure(self, server_id=None, server_host=None) -> MeasurementResult:
        """Measure network speed with the specified parameters."""
        # check that server_id or server_host is within the list of servers
        # since it is a static list, then only check that the server_id is an int and between 1 -> 5
        if server_id and (not isinstance(server_id, int) or not (1 <= server_id <= 5)):
            raise ValueError("server_id must be an integer between 1 and 6")
        if server_host and server_host not in [f"test{i}.example.com" for i in range(1, 6)]:
            raise ValueError("server_host must be a known test server")

        # Return a test measurement result
        # generate a server info (1) for id or host or fallback to 1
        return MeasurementResult(
            download_speed=self._download_speed,
            upload_speed=self._upload_speed,
            download_latency=self._download_latency,
            upload_latency=self._upload_latency,
            ping_latency=self._ping_latency,
            ping_jitter=self._ping_jitter,
            packet_loss=self._packet_loss,
            server_info=self._generate_server_info(server_id or (1 if not server_host else server_host[4:5])),
            persist_url="https://example.com/results/static-test-1234",
        )

# Register this provider
register_provider("static", StaticProvider)
