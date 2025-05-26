"""Command line interface for NetVelocimeter."""

from .commands import register_commands
from .main import app, entrypoint

# Register all CLI commands
register_commands(app)

# Public API for the CLI module
__all__ = ["entrypoint"]
