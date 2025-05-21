"""Output formatting utilities."""

from collections.abc import Sequence
import csv
from io import StringIO
import json
from typing import Any

from ..main import OutputFormat


def escape_whitespace(text: str) -> str:
    r"""Escape whitespace characters in a string.

    Replaces newlines, tabs, carriage returns, form feeds, vertical tabs, and backslashes
    with their `\` escaped representation for use in CSV/TSV values.

    Args:
        text: The input string to escape whitespace characters.

    Returns:
        The input string with whitespace characters escaped.
    """
    replacements = [
        ("\\", "\\\\"),  # Must escape backslashes first
        ("\n", "\\n"),
        ("\r", "\\r"),
        ("\t", "\\t"),
        ("\f", "\\f"),
        ("\v", "\\v"),
    ]

    for char, replacement in replacements:
        text = text.replace(char, replacement)
    return text


def format_records(records: Sequence[Any], fmt: OutputFormat, escape_ws: bool = False) -> str:
    """Format records according to the specified output format.

    Args:
        records: Sequence of record objects with a to_dict method
        fmt: Output format to use
        escape_ws: Whether to escape whitespace in CSV and TSV output

    Returns:
        Formatted string
    """
    if not records:
        return ""

    if fmt == OutputFormat.TEXT:
        return "\n\n".join(str(record) for record in records)

    elif fmt in (OutputFormat.CSV, OutputFormat.TSV):
        # Get dictionary fields from first record, remove the "raw" field
        field_names = [key for key in records[0].to_dict() if key != "raw"]

        # Write the header
        csv_output = StringIO()
        writer = csv.DictWriter(
            f=csv_output,
            fieldnames=field_names,
            extrasaction="ignore",
            dialect="unix" if fmt == OutputFormat.CSV else "excel-tab",
            lineterminator="\n",
        )
        writer.writeheader()

        # Write the record data
        for record in records:
            record_dict = record.to_dict()

            # if any key has a value which is a sequence, convert them to a string separated by newlines
            for key, value in record_dict.items():
                if isinstance(value, Sequence) and not isinstance(value, str):
                    value = "\n".join([str(v) for v in value])
                    if escape_ws:
                        value = escape_whitespace(value)
                    record_dict[key] = value

            writer.writerow(record_dict)

        return csv_output.getvalue()

    elif fmt == OutputFormat.JSON:
        json_data = [record.to_dict() for record in records]
        return json.dumps(json_data, indent=2, sort_keys=True)

    else:
        raise ValueError(f"Unsupported output format: {fmt}")
