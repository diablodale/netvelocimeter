"""Hashing utilities for creating unique identifiers."""

from base64 import urlsafe_b64encode
from hashlib import sha256


def hash_b64encode(data: str | bytes) -> str:
    """Hash data to create a unique identifier.

    Args:
        data: data to hash.

    Returns:
        A unique identifier for the data, encoded in url-safe base64 with padding removed.
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

    # truncate to a 22 chars gives ~128 bits of the hash
    # probability of a collision with 128 bits among even millions of terms is astronomically small
    return data_hash_base64[:22]
