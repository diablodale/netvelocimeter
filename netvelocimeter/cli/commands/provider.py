"""Provider commands for the NetVelocimeter CLI."""

import logging

import typer
from typer import Typer

from ... import list_providers
from ..main import state
from ..utils.formatters import format_records

# Get logger
logger = logging.getLogger(__name__)

# Create provider command group
provider_app = Typer(
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,
    help="Provider commands",
)


def register_provider_commands(app: Typer) -> None:
    """Register provider commands with the main app."""
    app.add_typer(provider_app, name="provider")


@provider_app.command(name="list")
def provider_list() -> None:
    """List all available providers."""
    logger.info("Listing available providers")

    providers = list_providers()
    logger.debug(f"Found {len(providers)} providers")

    # Display the providers
    if providers:
        typer.echo(format_records(providers, state.format, state.escape_ws))
    else:
        logger.error("No matching providers found.")
        raise typer.Exit(code=1)
