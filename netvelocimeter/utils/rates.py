"""Custom types for network rate, duration, percentage, etc."""

from datetime import timedelta
from typing import Any


class DataRateMbps(float):
    """Custom type for network data rate in Mbps (megabits per second).

    This class is used to ensure that download and upload speeds are always
    represented as floating-point numbers in units of megabits per second (Mbps).

    String formatting supports the standard Python format spec and appends a
    ' Mbps' suffix. The default is ".2f" for two decimal places.
    """

    # idiomatic way to prevent a __dict__ on immutable subclasses
    __slots__ = ()

    def __new__(cls, value: float) -> "DataRateMbps":
        """Create a new DataRateMbps instance."""
        return float.__new__(cls, value)

    def __format__(self, format_spec: str) -> str:
        """Format the value as a string with ' Mbps' suffix.

        Args:
            format_spec: The format specification for the float value.
                Defaults to ".2f" for two decimal places.

        Returns:
            A formatted string representing the data rate in Mbps.
        """
        # Default format spec if none provided
        if not format_spec:
            format_spec = ".2f"

        return f"{super().__format__(format_spec)} Mbps"


class Percentage(float):
    """Custom type for percentage values.

    This class is used to ensure that percentages are always
    represented as non-negative floating-point numbers. For example,
    a packet loss of 1.3% would be represented as `Percentage(1.3)`.

    String formatting supports the standard Python format spec and
    appends a ' %' suffix. The default is ".2f" for two decimal places.
    """

    # idiomatic way to prevent a __dict__ on immutable subclasses
    __slots__ = ()

    def __new__(cls, value: float) -> "Percentage":
        """Create a new Percentage instance."""
        return float.__new__(cls, value)

    def __format__(self, format_spec: str) -> str:
        """Format the value as a string with ' %' suffix.

        Args:
            format_spec: The format specification for the float value.
                Defaults to ".2f" for two decimal places.

        Returns:
            A formatted string representing the percentage value.
        """
        # Default format spec if none provided
        if not format_spec:
            format_spec = ".2f"

        return f"{super().__format__(format_spec)} %"


class TimeDuration(timedelta):
    """Custom type for network time duration.

    This class is used to represent durations related to network measurements,
    such as latency and jitter, ensuring they are always represented as timedelta
    objects. String formatting supports the standard Python format spec and
    custom unit suffixes. The default is ".2fms"
        - 'ss' for seconds
        - 'ms' for milliseconds (default)
        - 'us' for microseconds
        - 'ns' for nanoseconds
    """

    # Mapping of format suffixes to their units and conversion factors
    TIME_SPECS = {
        "ss": ("s", 1),
        "ms": ("ms", 1_000),
        "us": ("us", 1_000_000),
        "ns": ("ns", 1_000_000_000),
    }

    # idiomatic way to prevent a __dict__ on immutable subclasses
    __slots__ = ()

    def __new__(cls, *args: Any, **kwargs: Any) -> "TimeDuration":
        """Create a new TimeDuration instance."""
        # Pass all arguments directly to the parent timedelta constructor
        return timedelta.__new__(cls, *args, **kwargs)

    def __format__(self, format_spec: str) -> str:
        """Format the duration as a string in the specified unit and precision.

        The format_spec can be any valid Python format spec, optionally ending with
        'ss', 'ms', 'us', or 'ns' to specify the unit. For example:
            ".2fms" → milliseconds with 2 decimals
            ".0fus" → microseconds, rounded to int
            ".3fns" → nanoseconds, 3 decimals
            ".4fss" → seconds, 4 decimals
            "ms"    → milliseconds, integer

        If no unit is given, seconds are used.

        Args:
            format_spec: The format specification for the duration.
                Defaults to ".2fms" for milliseconds with two decimal places.

        Returns:
            A formatted string representing the duration in the requested unit.
        """
        # Default format spec if none provided
        if not format_spec:
            format_spec = ".2fms"

        # Check for recognized unit suffixes
        for candidate in self.TIME_SPECS:
            if format_spec.endswith(candidate):
                std_spec = format_spec[:-2] or ".0f"
                value = self.total_seconds() * self.TIME_SPECS[candidate][1]
                return f"{format(value, std_spec)} {self.TIME_SPECS[candidate][0]}"

        # No recognized unit suffix, treat as seconds
        value = self.total_seconds()
        return format(value, format_spec)
