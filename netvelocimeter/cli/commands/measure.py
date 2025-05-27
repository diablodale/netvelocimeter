"""Measurement commands for the NetVelocimeter CLI."""

from typing import Annotated

import typer
from typer import Typer

from ... import NetVelocimeter
from ...utils.logger import get_logger
from ..main import state
from ..utils.formatters import format_records

# Get logger for measure commands
logger = get_logger(__name__)

# Create measure command group
measure_app = Typer(
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,
    help="Measurement commands",
)


def register_measure_commands(app: Typer) -> None:
    """Register measurement commands with the main app."""
    app.add_typer(measure_app, name="measure")


# TODO --server-id and --server-host options for measurements
@measure_app.command(name="run")
def measure_run(
    server_id: Annotated[
        str | None,
        typer.Option(
            "--server-id", show_default=False, help="Provider server id to use for measurement"
        ),
    ] = None,
    server_host: Annotated[
        str | None,
        typer.Option(
            "--server-host", show_default=False, help="Provider server host to use for measurement"
        ),
    ] = None,
) -> None:
    """Run a measurement with the selected provider."""
    logger.info(f"Running measurement for provider '{state.provider}'")

    nv = NetVelocimeter(
        provider=state.provider,
        bin_root=state.bin_root,
        config_root=state.config_root,
    )

    # Perform the measurement
    result = nv.measure(server_id=server_id, server_host=server_host)
    logger.debug(f"Measurement result: {result.raw}")

    # Display the result
    if result:
        typer.echo(format_records([result], state.format, state.escape_ws))
    else:
        logger.warning("No results.")
        raise typer.Exit(code=1)
