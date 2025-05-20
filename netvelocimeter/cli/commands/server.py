"""Server commands for the NetVelocimeter CLI."""

import typer
from typer import Typer

from ... import NetVelocimeter
from ...utils.logger import get_logger
from ..main import state
from ..utils.formatters import format_records

# Get logger for server commands
logger = get_logger("cli.server")

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
    """Servers for the selected provider."""
    logger.debug(f"Listing servers for provider: {state['provider']}")

    nv = NetVelocimeter(
        provider=state["provider"],
        bin_root=state["bin_root"],
        config_root=state["config_root"],
    )
    # BUGBUG remove auto accept
    nv.accept_terms(nv.legal_terms())

    # Get the list of servers
    servers = nv.servers
    if not servers:
        logger.warning("No servers found for provider: %s", state["provider"])
        typer.echo("No servers available for the selected provider.")
        raise typer.Exit(code=1)

    # Print the list of servers
    logger.info("Found %d servers", len(servers))
    typer.echo(format_records(servers, state["format"]))
