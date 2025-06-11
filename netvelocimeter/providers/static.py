"""Static provider usually used for testing."""

import logging
import re

from packaging.version import Version

from ..core import register_provider
from ..legal import (
    LegalTerms,
    LegalTermsCategory,
    LegalTermsCategoryCollection,
    LegalTermsCollection,
)
from ..utils.binary_manager import BinaryManager
from ..utils.rates import DataRateMbps, Percentage, TimeDuration
from .base import BaseProvider, MeasurementResult, ServerIDType, ServerInfo

# Get logger
logger = logging.getLogger(__name__)


class StaticProvider(BaseProvider):
    """Configurable provider usually for testing, does not require external dependencies or network.

    All fields default to test values, set any to None to omit them.
    Five test servers with ids 1 -> 5 are available.
    All constructor parameters are persisted for each instance of this class.
    """

    def __init__(
        self,
        *,
        eula_text: str | None = "Test EULA",
        eula_url: str | None = "https://example.com/eula",
        terms_text: str | None = "Test Terms",
        terms_url: str | None = "https://example.com/terms",
        privacy_text: str | None = "Test Privacy",
        privacy_url: str | None = "https://example.com/privacy",
        download_speed: DataRateMbps = DataRateMbps(100.0),  # noqa: B008
        upload_speed: DataRateMbps = DataRateMbps(50.0),  # noqa: B008
        download_latency: TimeDuration = TimeDuration(milliseconds=30.0),  # noqa: B008
        upload_latency: TimeDuration = TimeDuration(milliseconds=60.0),  # noqa: B008
        ping_latency: TimeDuration = TimeDuration(milliseconds=25.0),  # noqa: B008
        ping_jitter: TimeDuration = TimeDuration(milliseconds=20.0),  # noqa: B008
        packet_loss: Percentage = Percentage(1.3),  # noqa: B008
        version: str = "1.2.3+c0ffee",
        config_root: str | None = None,
        bin_root: str | None = None,
    ):
        r"""Initialize a configurable test provider.

        Args:
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
            config_root: Directory to store configuration, e.g. legal acceptance
                - None: Use default location (%%APPDATA%%\netvelocimeter or ~/.config/netvelocimeter)
                - str: Custom directory path
            bin_root: Custom binary cache root directory (not used in this provider)
        """
        # Call the base provider constructor
        super().__init__(config_root=config_root)

        # log warning that is used for testing purposes
        logger.warning(
            "StaticProvider is used for testing purposes, it does not require network access."
        )

        #  persist params
        self._download_speed = download_speed
        self._upload_speed = upload_speed
        self._download_latency = download_latency
        self._upload_latency = upload_latency
        self._ping_latency = ping_latency
        self._ping_jitter = ping_jitter
        self._packet_loss = packet_loss
        self.__version = Version(version)

        # Only add terms that have content
        self._TERMS_COLLECTION = LegalTermsCollection()
        if eula_text or eula_url:
            # Add EULA terms if requested
            self._TERMS_COLLECTION.append(
                LegalTerms(text=eula_text, url=eula_url, category=LegalTermsCategory.EULA)
            )
        if terms_text or terms_url:
            # Add service terms if requested
            self._TERMS_COLLECTION.append(
                LegalTerms(text=terms_text, url=terms_url, category=LegalTermsCategory.SERVICE)
            )
        if privacy_text or privacy_url:
            # Add privacy terms if requested
            self._TERMS_COLLECTION.append(
                LegalTerms(text=privacy_text, url=privacy_url, category=LegalTermsCategory.PRIVACY)
            )

        # create an unused binary manager
        self._BINARY_MANAGER = BinaryManager(StaticProvider, bin_root=bin_root)

    @property
    def _version(self) -> Version:
        """Get the provider version.

        Returns:
            Version for this provider
        """
        return self.__version

    def _legal_terms(
        self, categories: LegalTermsCategory | LegalTermsCategoryCollection = LegalTermsCategory.ALL
    ) -> LegalTermsCollection:
        """Get legal terms for this provider.

        Args:
            categories: Category(s) of terms to retrieve. Defaults to ALL.

        Returns:
            Collection of legal terms that match the requested category
        """
        # Check if a requested category is ALL
        if categories == LegalTermsCategory.ALL or LegalTermsCategory.ALL in categories:
            return self._TERMS_COLLECTION

        # Return the terms collection filtered by the requested category
        return [term for term in self._TERMS_COLLECTION if term.category in categories]

    def _generate_server_info(self, server_num: int) -> ServerInfo:
        """Generate a test server info object with the given server number."""
        return ServerInfo(
            name=f"Test Server {server_num}",
            id=server_num,
            host=f"test{server_num}.example.com",
            location=f"Test Location {server_num}",
            country="Test Country",
        )

    @property
    def _servers(self) -> list[ServerInfo]:
        """Get list of available servers."""
        return [self._generate_server_info(i) for i in range(1, 6)]

    def _measure(
        self, server_id: ServerIDType | None = None, server_host: str | None = None
    ) -> MeasurementResult:
        """Measure network speed with the specified parameters.

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
            id=f"static-test-{server_num}-{hash(self)}",
        )


# Register this provider
register_provider("static", StaticProvider)
