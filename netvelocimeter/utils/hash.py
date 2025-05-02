"""Hashing utilities for creating unique identifiers."""

from base64 import urlsafe_b64encode
from hashlib import sha256


def hash_b64encode(data: str | bytes, truncate: int | None = 22) -> str:
    """Hash data to create a unique identifier.

    Args:
        data: data to hash.
        truncate: integer character length of the hash to return or `None` for the full hash.
        Default is 22 characters which is ~128 bits of the hash. This is sufficient to avoid
            collisions for most practical applications.

    Returns:
        A unique identifier for the data, encoded in url-safe base64 with padding `=` removed.
        Url-safe alphabet uses `-` instead of `+` and `_` instead of `/`.
    """
    # validate and covert data
    if isinstance(data, str):
        data = data.encode("utf-8")
    elif not isinstance(data, bytes):
        raise ValueError("Data must be a string or bytes.")

    # Hash the data
    data_hash = sha256(data).digest()

    # Convert to URL-safe base64 and remove padding
    # This creates shorter directory names that are still filesystem-safe
    data_hash_base64 = urlsafe_b64encode(data_hash).decode("ascii").rstrip("=")

    # truncate the hash to the specified length
    return data_hash_base64[:truncate]
