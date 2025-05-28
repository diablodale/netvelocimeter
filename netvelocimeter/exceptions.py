"""Exceptions for the NetVelocimeter package."""


class LegalAcceptanceError(Exception):
    """Exception raised when legal agreements haven't been accepted."""

    def __init__(self, msg: str = "Must accept all legal terms before use.") -> None:
        """Initialize the LegalAcceptanceError with a message."""
        super().__init__(msg)


class MeasurementError(Exception):
    """Exception raised when a measurement fails."""

    pass


class PlatformNotSupported(Exception):
    """Exception raised when the platform is not supported."""

    pass
