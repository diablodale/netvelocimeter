"""Module for MeasurementResult class."""

from dataclasses import dataclass, field
from typing import Any

from ..utils.formatters import TwoColumnFormatMixin
from ..utils.rates import DataRateMbps, Percentage, TimeDuration
from .server_info import ServerInfo


@dataclass
class MeasurementResult(TwoColumnFormatMixin):
    """Result of a network measurement.

    Attributes:
        download_speed: Download speed in Mbps (megabits per second).
        upload_speed: Upload speed in Mbps.
        download_latency: Download latency as TimeDuration.
        upload_latency: Upload latency as TimeDuration.
        ping_latency: Ping latency as TimeDuration.
        ping_jitter: Ping jitter as TimeDuration.
        packet_loss: Packet loss percentage.
        server_info: Information about the server used for testing.
        persist_url: URL to view test results.
        id: Provider-assigned measurement ID.
        raw: Raw provider result data.
    """

    download_speed: DataRateMbps
    """Download speed in Mbps (megabits per second)."""

    upload_speed: DataRateMbps
    """Upload speed in Mbps (megabits per second)."""

    download_latency: TimeDuration | None = None
    """Download latency as TimeDuration."""

    upload_latency: TimeDuration | None = None
    """Upload latency as TimeDuration."""

    ping_latency: TimeDuration | None = None
    """Ping latency as TimeDuration."""

    ping_jitter: TimeDuration | None = None
    """Ping jitter as TimeDuration."""

    packet_loss: Percentage | None = None
    """Packet loss percentage as float from 0.0 to 100.0."""

    server_info: ServerInfo | None = None
    """Information about the server used for testing."""

    persist_url: str | None = None
    """Provider-assigned URL to view test results."""

    id: str | None = None
    """Provider-assigned measurement ID."""

    raw: dict[str, Any] | None = None
    """Raw provider result data."""

    _format_prefix: str = field(default="measure_", init=False)

    def __post_init__(self) -> None:
        """Ensure download and upload speeds are set."""
        # Ensure that download and upload speeds are provided, and they are DataRateMbps instances
        if self.download_speed is None or not isinstance(self.download_speed, DataRateMbps):
            raise ValueError("Download speed must be a DataRateMbps instance")
        if self.upload_speed is None or not isinstance(self.upload_speed, DataRateMbps):
            raise ValueError("Upload speed must be a DataRateMbps instance")

        # Ensure that latencies and jitter are None or TimeDuration instances
        if self.download_latency is not None and not isinstance(
            self.download_latency, TimeDuration
        ):
            raise ValueError("Download latency must be a TimeDuration instance")
        if self.upload_latency is not None and not isinstance(self.upload_latency, TimeDuration):
            raise ValueError("Upload latency must be a TimeDuration instance")
        if self.ping_latency is not None and not isinstance(self.ping_latency, TimeDuration):
            raise ValueError("Ping latency must be a TimeDuration instance")
        if self.ping_jitter is not None and not isinstance(self.ping_jitter, TimeDuration):
            raise ValueError("Ping jitter must be a TimeDuration instance")

        # Ensure packet loss is None or Percentage instance
        if self.packet_loss is not None and not isinstance(self.packet_loss, Percentage):
            raise ValueError("Packet loss must be a Percentage instance")

        # Ensure server_info is None or ServerInfo instance
        if self.server_info is not None and not isinstance(self.server_info, ServerInfo):
            raise ValueError("Server info must be a ServerInfo instance")

        # Ensure persist_url is None or a string
        if self.persist_url is not None and not isinstance(self.persist_url, str):
            raise ValueError("Persist URL must be a string")

        # Ensure id is None or a string
        if self.id is not None and not isinstance(self.id, str):
            raise ValueError("ID must be a string")

        # Ensure raw is None or a dictionary
        if self.raw is not None and not isinstance(self.raw, dict):
            raise ValueError("Raw data must be a dictionary")
