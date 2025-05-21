"""Measurement commands for the NetVelocimeter CLI."""

from typer import Typer

from ...utils.logger import get_logger
from ..main import state

# Get logger for measure commands
logger = get_logger("cli.measure")

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


@measure_app.command(name="run")
def measure_run() -> None:
    """Run a measurement with the selected provider."""
    logger.info("Starting measurement with provider: %s", state.provider)
    # Implementation goes here
