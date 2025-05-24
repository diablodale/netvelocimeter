"""Module for ProviderInfo class."""

from dataclasses import dataclass, field
from typing import Any

from ..utils.formatters import TwoColumnFormatMixin


@dataclass
class ProviderInfo(TwoColumnFormatMixin):
    """Information about a provider.

    Attributes:
        name: Name of the provider
        description: Description of the provider
    """

    name: str
    description: list[str]
    _format_prefix: str = field(default="provider_", init=False)

    def __post_init__(self) -> None:
        """Ensure name and description are not empty."""
        if not self.name or not self.description:
            raise ValueError("Name and description cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        """Convert the provider info to a dictionary.

        Returns:
            A dictionary representation of the provider info.
        """
        return {
            "name": self.name,
            "description": self.description,
        }
