"""Pretty formatters used in class __format__ methods."""

from collections.abc import Sequence
from enum import Enum

from netvelocimeter.utils.logger import get_logger

# Get logger for measure commands
logger = get_logger("cli.measure")


def pretty_print_two_columns(obj: object, prefix: str | None = None) -> str:
    """Pretty print any dataclass or class with __dict__ in two columns.

    The first column contains the field names (ending with a colon), left-justified and padded to field_width.
    The second column contains the field values, left-justified.

    Args:
        obj: The object to pretty print.
        prefix: A string to prepend to each field name.
            - None will use the `_format_prefix` attribute on the object if it exists,
              or default to an empty string.
            - A string will be used as the prefix for each field name.

    Returns:
        A string with the pretty-printed fields.
    """
    # Prefer dataclasses, fallback to __dict__
    if hasattr(obj, "__dataclass_fields__"):
        fields = obj.__dataclass_fields__.keys()
    elif hasattr(obj, "__dict__"):
        fields = obj.__dict__.keys()
    else:
        raise TypeError(
            f"Object of type {type(obj).__name__} is not supported for pretty printing."
        )

    # use the _format_prefix attribute if it exists, otherwise default to empty string
    if prefix is None:
        prefix = getattr(obj, "_format_prefix", "")
        logger.info(f"Using prefix: {prefix}")

    # remove raw and private fields
    fields = [name for name in fields if not name.startswith("_") and name != "raw"]

    # calc field width for column 1
    field_width = max(len(name) for name in fields) + len(prefix) + 1

    lines = []
    for name in fields:
        # get the value of the field
        value = getattr(obj, name)
        if value is None:
            continue

        # recurse if the value is a dataclass or has __dict__
        logger.debug(f"Processing field '{name}' with value: {value!r}")
        if not isinstance(value, Enum) and (
            hasattr(value, "__dict__") or hasattr(value, "__dataclass_fields__")
        ):
            # recurse to pretty print nested dataclass or object and use the class' format prefix
            lines.append(pretty_print_two_columns(value))
            continue

        # else normalize to sequence
        if isinstance(value, str) or not isinstance(value, Sequence):
            value = [value]

        # iterate over the values, printing the field name on the first line
        iterator = iter(value)
        lines.append(f"{prefix + name + ':':<{field_width}} {next(iterator)}")
        for line in iterator:
            # Indent subsequent lines
            lines.append(" " * field_width + f" {line}")

    # return the formatted string, one line per field
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
