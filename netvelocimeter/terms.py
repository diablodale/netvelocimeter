"""Models for handling legal terms and their acceptance."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import os
from typing import Any

from .utils.hash import hash_b64encode
from .utils.xdg import XDGCategory


class LegalTermsCategory(str, Enum):
    """Categories of legal terms."""

    EULA = "eula"
    """End User License Agreement"""

    SERVICE = "service"
    """Service Terms of Use"""

    PRIVACY = "privacy"
    """Privacy Policy"""

    NDA = "nda"
    """Non-Disclosure Agreement"""

    OTHER = "other"
    """Other legal terms that do not fit into predefined categories"""

    ALL = "all"
    """Special value to represent all categories"""


LegalTermsCategoryCollection = list[LegalTermsCategory]


@dataclass
class LegalTerms:
    """Representation of a single legal terms document."""

    category: LegalTermsCategory
    text: str | None = None
    url: str | None = None

    def __post_init__(self) -> None:
        """Post-initialization checks for the LegalTerms class."""
        # Ensure at least one of text or URL is provided
        if not self.text and not self.url:
            raise ValueError("Either LegalTerms text or URL must be provided")

        # Ensure category is valid
        if not isinstance(self.category, LegalTermsCategory):
            raise ValueError(f"Invalid category: {self.category}")

    def __str__(self) -> str:
        """Return a string representation of the legal terms.

        Returns:
            A string with the category and either text or URL.
        """
        parts = [f"category: {self.category.name}"]
        if self.text:
            parts.append(f"text: {self.text}")
        if self.url:
            parts.append(f"url: {self.url}")
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert the LegalTerms object to a dictionary.

        Returns:
            A dictionary representation of the LegalTerms object.
        """
        return {
            "category": self.category.name,
            "text": self.text,
            "url": self.url,
        }

    def unique_id(self, methodology_version: int = 1) -> str:
        """Compute a stable lookup id for legal terms content to use with cache and persistence.

        Args:
            methodology_version: Version of the hash methodology to use. Only `1` is supported.

        Returns:
            A unique identifier for the legal terms content. The id is partitioned by `/` characters
            to allow for parsing and partitioned storage on filesystems.

        Raises:
            ValueError: If the methodology version is not supported.

        Example:
            >>> terms = LegalTerms(text="Sample terms", category=LegalTermsCategory.EULA)
            >>> terms.unique_id()
            '1/abc123...'
        """
        # Validate methodology version
        if methodology_version != 1:
            raise ValueError(f"Unsupported methodology version: {methodology_version}")

        # Use a combination of text, URL, and category to create a unique hash
        content = f"{self.text or ''}|{self.url or ''}|{self.category.name}"

        # construct a unique identifier
        return f"1/{hash_b64encode(content)}"


# Type alias for a collection of LegalTerms
LegalTermsCollection = list[LegalTerms]


class AcceptanceTracker:
    """Tracks which legal terms have been accepted using the version directory approach."""

    def __init__(self, config_root: str | None = None) -> None:
        r"""Initialize an acceptance tracker.

        Args:
            config_root: Directory to store configuration, e.g. legal acceptance
                - None: Use default location (%%APPDATA%%\netvelocimeter or ~/.config/netvelocimeter)
                - str: Custom directory path
        """
        # resolve config_root
        if config_root:
            # expand environment variables and user directory
            candidate = os.path.expandvars(config_root)
            candidate = os.path.expanduser(candidate)

            # check if the path is absolute
            if not os.path.isabs(candidate):
                raise ValueError(f"Invalid config root: {config_root}")
        else:
            # Use platform-specific XDG directory
            candidate = XDGCategory.CONFIG.resolve_path("netvelocimeter")

        # In-memory dict cache of already checked acceptances could be created, but
        # that introduces a need for thread-safety for read+write into the dict.
        # Primary use cases do not need an in-memory cache, so we use only the file system.

        # normalize the path to avoid issues with different path separators and makedirs() limitations
        candidate = os.path.normpath(candidate)

        # Ensure the base directory exists
        os.makedirs(candidate, mode=0o750, exist_ok=True)
        self._config_root = candidate

    def _acceptance_file_path(self, terms_id: str) -> str:
        """Get the path to the json file for a specific terms acceptance.

        Args:
            terms_id: terms id string with partitions separated by `/`

        Returns:
            Absolute path to the json acceptance file
        """
        # Return full path to the acceptance file
        return os.path.join(self._config_root, *terms_id.split("/")) + ".json"

    def is_recorded(self, terms_or_collection: LegalTerms | LegalTermsCollection) -> bool:
        """Check if the terms have been recorded as accepted.

        Args:
            terms_or_collection: A single LegalTerms object or collection of LegalTerms

        Returns:
            True if all terms have been accepted or the collection is empty.
            False otherwise.

        Raises:
            TypeError: If the input is not a LegalTerms or LegalTermsCollection

        Examples:
            >>> terms = LegalTerms(text="Sample terms", category=LegalTermsCategory.EULA)
            >>> tracker = AcceptanceTracker()
            >>> tracker.is_recorded(terms)
            False
            >>> tracker.record(terms)
            >>> tracker.is_recorded(terms)
            True
            >>> collection = [terms, LegalTerms(text="More terms", category=LegalTermsCategory.SERVICE)]
            >>> tracker.is_recorded(collection)
            False
            >>> tracker.record(collection)
            >>> tracker.is_recorded(collection)
            True
            >>> tracker.is_recorded([])
            True
        """
        if isinstance(terms_or_collection, LegalTerms):
            # Get the unique id for the terms
            terms_id = terms_or_collection.unique_id()

            # Check if acceptance file for that id exists
            file_path = self._acceptance_file_path(terms_id)
            return os.path.exists(file_path)

        elif isinstance(terms_or_collection, list):
            # Empty collection is considered accepted; easy use for providers that have no legal terms
            if not terms_or_collection:
                return True

            # All terms in collection must be accepted
            return all(self.is_recorded(term) for term in terms_or_collection)

        raise TypeError(
            f"Expected LegalTerms or LegalTermsCollection, got {type(terms_or_collection)}"
        )

    def record(self, terms_or_collection: LegalTerms | LegalTermsCollection) -> None:
        """Record acceptance of terms.

        Args:
            terms_or_collection: A single LegalTerms object or collection of LegalTerms to record
        """
        if isinstance(terms_or_collection, LegalTerms):
            # Check if terms are already recorded
            if self.is_recorded(terms_or_collection):
                return

            # Create acceptance record
            data = {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }

            # Get the acceptance file path
            file_path = self._acceptance_file_path(terms_or_collection.unique_id())

            # Ensure directories exist
            os.makedirs(os.path.dirname(file_path), mode=0o750, exist_ok=True)

            try:
                # Create file with exclusive mode to avoid race conditions
                with open(file_path, "x", encoding="utf-8") as f:
                    json.dump(data, f, indent=None, separators=(",", ":"))

            except FileExistsError:
                # Another process beat us to accepting these terms
                pass

        elif isinstance(terms_or_collection, list):
            for terms in terms_or_collection:
                self.record(terms)

        else:
            raise TypeError(
                f"Expected LegalTerms or LegalTermsCollection, got {type(terms_or_collection)}"
            )
