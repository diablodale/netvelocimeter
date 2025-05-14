"""CLI command registry."""

import typer

# from .legal import register_legal_commands
from .measure import register_measure_commands
from .server import register_server_commands


def register_commands(app: typer.Typer) -> None:
    """Register all CLI commands with the main app."""
    register_server_commands(app)
    register_measure_commands(app)
    # register_legal_commands(app)


__all__ = ["register_commands"]
