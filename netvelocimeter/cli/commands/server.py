"""Server commands for the NetVelocimeter CLI."""

import logging

import typer
from typer import Typer

from ... import NetVelocimeter
from ..main import state
from ..utils.formatters import format_records

# Get logger
logger = logging.getLogger(__name__)

# Create server command group
server_app = Typer(
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,  # hinder disclosing secrets
    help="Server commands",
)


def register_server_commands(app: Typer) -> None:
    """Register server commands with the main app."""
    app.add_typer(server_app, name="server")


@server_app.command(name="list")
def server_list() -> None:
    """List servers for the selected provider."""
    logger.info(f"Listing servers for provider '{state.provider}'")

    nv = NetVelocimeter(
        provider=state.provider,
        bin_root=state.bin_root,
        config_root=state.config_root,
    )

    # Get the list of servers
    servers = nv.servers
    logger.debug(f"Found {len(servers)} servers")

    # Display the list of servers
    if servers:
        typer.echo(format_records(servers, state.format, state.escape_ws))
    else:
        logger.error("No matching servers found.")
        raise typer.Exit(code=1)
