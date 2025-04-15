"""
Base class for all speed test providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class MeasurementResult:
    """Result of a network measurement."""

    download_speed: Optional[float] = None  # in Mbps
    upload_speed: Optional[float] = None    # in Mbps
    latency: Optional[float] = None         # in ms
    jitter: Optional[float] = None          # in ms
    packet_loss: Optional[float] = None     # as percentage
    server_info: Optional[Dict] = None      # server details
    raw_result: Optional[Dict] = None       # raw provider result

    def __str__(self) -> str:
        """Return a string representation of the measurement result."""
        parts = []
        if self.download_speed is not None:
            parts.append(f"Download: {self.download_speed:.2f} Mbps")
        if self.upload_speed is not None:
            parts.append(f"Upload: {self.upload_speed:.2f} Mbps")
        if self.latency is not None:
            parts.append(f"Latency: {self.latency:.2f} ms")
        if self.jitter is not None:
            parts.append(f"Jitter: {self.jitter:.2f} ms")
        if self.packet_loss is not None:
            parts.append(f"Packet Loss: {self.packet_loss:.2f}%")

        return ", ".join(parts)


class BaseProvider(ABC):
    """Base class for all network measurement providers."""

    def __init__(self, binary_dir: str):
        """
        Initialize the provider.

        Args:
            binary_dir: Directory to store provider binaries.
        """
        self.binary_dir = binary_dir

    @abstractmethod
    def measure(self) -> MeasurementResult:
        """
        Perform a complete network measurement.

        Returns:
            A MeasurementResult object containing the measurement results.
        """
        pass

    @abstractmethod
    def measure_download(self) -> float:
        """
        Measure download speed.

        Returns:
            Download speed in Mbps.
        """
        pass

    @abstractmethod
    def measure_upload(self) -> float:
        """
        Measure upload speed.

        Returns:
            Upload speed in Mbps.
        """
        pass

    @abstractmethod
    def measure_latency(self) -> float:
        """
        Measure network latency.

        Returns:
            Latency in ms.
        """
        pass
