"""Pretty formatters used in class __format__ methods."""

from collections.abc import Sequence
from enum import Enum

from netvelocimeter.utils.logger import get_logger

# Get logger for measure commands
logger = get_logger(__name__)


def _flatten_fields(obj: object, prefix: str = "") -> tuple[list[tuple[str, object]], int]:
    """Flatten the object graph into a list of (field_name, value) and find max width.

    Args:
        obj: The object to flatten, which can be a dataclass or any class with __dict__.
        prefix: Prefix to prepend to field names. Nested objects can set this via their `_format_prefix` attribute.

    Returns:
        Tuple:
            1. list of (field_name, value) pairs
            2. maximum width of all field names + 1 to account for a colon after every field name
    """
    fields = []
    max_width = 0

    if hasattr(obj, "__dataclass_fields__"):
        field_names = obj.__dataclass_fields__.keys()
    elif hasattr(obj, "__dict__"):
        field_names = obj.__dict__.keys()
    else:
        return [], 0

    field_names = [name for name in field_names if not name.startswith("_") and name != "raw"]

    for name in field_names:
        value = getattr(obj, name)
        if value is None:
            continue
        field_label = f"{prefix}{name}:"
        max_width = max(max_width, len(field_label))
        # Recurse for nested objects
        if not isinstance(value, Enum) and (
            hasattr(value, "__dict__") or hasattr(value, "__dataclass_fields__")
        ):
            nested_prefix = getattr(value, "_format_prefix", "")
            logger.debug(f"Flatten nested: {name} type={type(value)} prefix={nested_prefix}")
            nested_fields, nested_width = _flatten_fields(value, nested_prefix)
            fields.extend(nested_fields)
            max_width = max(max_width, nested_width)
        else:
            fields.append((field_label, value))
    return fields, max_width


def pretty_print_two_columns(obj: object, prefix: str) -> str:
    """Pretty print any dataclass or class with __dict__ in two columns, with correct alignment.

    Args:
        obj: The object to format, which can be a dataclass or any class with __dict__.
        prefix: Prefix to prepend to field names. Nested objects can set this via their `_format_prefix` attribute.

    Returns:
        A formatted string representing the object in two columns.
    """
    fields, field_width = _flatten_fields(obj, prefix)
    lines = []
    for field_label, value in fields:
        # Normalize value to sequence for multi-line values
        if isinstance(value, str) or not isinstance(value, Sequence):
            value = [value]

        # Handle single-line and multi-line values
        iterator = iter(value)
        lines.append(f"{field_label:<{field_width}} {next(iterator)}")
        for line in iterator:
            lines.append(" " * field_width + f" {line}")

    # Return the formatted string with each line separated by a newline
    return "\n".join(lines)


class TwoColumnFormatMixin:
    """Mixin to provide a __format__ method for two-column formatting."""

    def __format__(self, format_spec: str) -> str:
        """Format the object as a two-column string.

        Args:
            format_spec: Format specification string.

        Returns:
            A formatted string representing the object.
        """
        return format(pretty_print_two_columns(self, ""), format_spec)
