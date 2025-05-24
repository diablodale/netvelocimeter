"""Module for ServerInfo class."""

from dataclasses import dataclass, field
from typing import Any

from ..utils.formatters import TwoColumnFormatMixin

# type alias for server ID
ServerIDType = int | str


@dataclass
class ServerInfo(TwoColumnFormatMixin):
    """Information about a speed test server.

    Attributes:
        name: Descriptive name of the server.
        id: Server ID (can be int or str).
        host: Hostname or IP address of the server.
        location: Location name of the server.
        country: Country name of the server.
        raw: Raw provider-specific server data.
    """

    name: str
    id: ServerIDType | None = None
    host: str | None = None
    location: str | None = None
    country: str | None = None
    raw: dict[str, Any] | None = None
    _format_prefix: str = field(default="server_", init=False)

    def __post_init__(self) -> None:
        """Require name to be set."""
        if not self.name:
            raise ValueError("Name cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        """Convert the server info to a dictionary."""
        # do not change key names as they are used in the CSV, TSV, and JSON output
        # "name" must be first
        return {
            "name": self.name,
            "id": self.id,
            "host": self.host,
            "location": self.location,
            "country": self.country,
            "raw": self.raw,
        }
