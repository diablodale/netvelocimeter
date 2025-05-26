"""Output format for the command line interface."""

from enum import Enum


class OutputFormat(str, Enum):
    """Output format for the command line interface."""

    TEXT = "text"
    CSV = "csv"
    TSV = "tsv"
    JSON = "json"
