"""Models for handling legal terms and their acceptance."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, auto
import hashlib


class LegalTermsCategory(Enum):
    """Categories of legal terms."""

    EULA = auto()
    SERVICE = auto()
    PRIVACY = auto()
    NDA = auto()
    OTHER = auto()
    ALL = auto()  # Special value to represent all categories


@dataclass
class LegalTerms:
    """Representation of a single legal terms document."""

    text: str | None = None
    url: str | None = None
    category: LegalTermsCategory = LegalTermsCategory.OTHER

    def compute_hash(self) -> str:
        """Compute a stable hash of the legal terms content."""
        # Use a combination of text, URL, and category to create a unique hash
        content = f"{self.text or ''}|{self.url or ''}|{self.category.name}"
        # label it with `1` as the hash methodology version
        return f"1:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"  # TODO base64 encode


# Type alias for a collection of LegalTerms
LegalTermsCollection = list[LegalTerms]


class AcceptanceTracker:
    """Tracks which legal terms have been accepted."""

    def __init__(self) -> None:
        """Initialize an empty acceptance tracker."""
        # Maps term hash to timestamp of acceptance
        self._acceptances: dict[str, datetime] = {}

    def is_recorded(self, terms_or_collection: LegalTerms | LegalTermsCollection) -> bool:
        """Check if the terms have been recorded as accepted.

        Args:
            terms_or_collection: A single LegalTerms object or collection of LegalTerms

        Returns:
            True if all terms have been accepted, False otherwise
        """
        if isinstance(terms_or_collection, LegalTerms):
            terms_hash = terms_or_collection.compute_hash()
            return terms_hash in self._acceptances

        elif isinstance(terms_or_collection, list):
            # Empty collection is considered accepted
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
            terms_hash = terms_or_collection.compute_hash()
            self._acceptances[terms_hash] = datetime.now(timezone.utc)
        elif isinstance(terms_or_collection, list):
            for terms in terms_or_collection:
                self.record(terms)
        else:
            raise TypeError(
                f"Expected LegalTerms or LegalTermsCollection, got {type(terms_or_collection)}"
            )
