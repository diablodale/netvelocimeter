"""Exceptions for the NetVelocimeter package."""


class LegalAcceptanceError(Exception):
    """Exception raised when legal agreements haven't been accepted."""

    pass


class MeasurementError(Exception):
    """Exception raised when a measurement fails."""

    pass


class PlatformNotSupported(Exception):
    """Exception raised when the platform is not supported."""

    pass
