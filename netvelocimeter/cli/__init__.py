"""Command line interface for NetVelocimeter."""

from .commands import register_commands
from .main import OutputFormat, app, state

# Register all CLI commands
register_commands(app)

__all__ = ["app", "state", "OutputFormat"]

# netvelocimeter --provider=ookla measure
# netvelocimeter --provider=ookla server list
# netvelocimeter --provider=ookla legal list

# netvelocimeter measure
# netvelocimeter server list
# netvelocimeter legal list

# netvelocimeter measure ookla
# netvelocimeter server list ookla
# netvelocimeter legal list ookla

# https://typer.tiangolo.com/tutorial/arguments/default/
