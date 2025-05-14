"""Output formatting utilities."""

from collections.abc import Sequence
import csv
from io import StringIO
import json
from typing import Any

from ..main import OutputFormat


def format_records(records: Sequence[Any], fmt: OutputFormat) -> str:
    """Format records according to the specified output format.

    Args:
        records: Sequence of record objects with a to_dict method
        fmt: Output format to use

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
            writer.writerow(record.to_dict())

        return csv_output.getvalue()

    elif fmt == OutputFormat.JSON:
        json_data = [record.to_dict() for record in records]
        return json.dumps(json_data, indent=2)

    else:
        raise ValueError(f"Unsupported output format: {fmt}")
