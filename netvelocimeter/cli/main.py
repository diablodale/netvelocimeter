"""Command line interface for NetVelocimeter."""

import logging
from pathlib import Path
from typing import Annotated

from click import Choice
import typer

from .. import __version__ as version_string, list_providers
from ..utils.xdg import XDGCategory
from .utils.logger import setup_cli_logging
from .utils.output_format import OutputFormat

# Define constants
BIN_ROOT_DEFAULT = Path(XDGCategory.BIN.resolve_path("netvelocimeter-cache"))
CONFIG_ROOT_DEFAULT = Path(XDGCategory.CONFIG.resolve_path("netvelocimeter"))
AVAILABLE_PROVIDERS = [provider.name for provider in list_providers()]

# Get logger
logger = logging.getLogger(__name__)


class CliState:
    """State for the command line interface."""

    def __init__(self) -> None:
        """Initialize the CLI state with default values."""
        self.bin_root: Path = BIN_ROOT_DEFAULT
        self.config_root: Path = CONFIG_ROOT_DEFAULT
        self.escape_ws: bool = False
        self.format: OutputFormat = OutputFormat.TEXT
        self.provider: str = "ookla"
        self.quiet: bool = False


# Running in a PyInstaller bundle
# IN_PYINSTALL_BUNDLE = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# state container instance
state: CliState = CliState()

#########################
#### Global Commands ####
#########################

# Define the Typer app
app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,  # hinder disclosing secrets
)


def entrypoint() -> None:
    """Entry point for the CLI application.

    Exceptions are caught and logged, with behavior depending on the log level.
    If the log level is DEBUG, the exception is raised to show the traceback.
    SystemExit() is a sibling of Exception and is not caught here, allowing it to propagate normally.
    """
    try:
        app()
    except Exception as ex:
        # Log the exception as critical since the application will not continue
        logger.critical(str(ex))

        # If the log level is DEBUG, raise the exception to show the traceback
        if logger.getEffectiveLevel() <= logging.DEBUG:
            raise

        # Otherwise, exit with an error code
        exit(1)


@app.callback(invoke_without_command=True)
def global_options(
    bin_root: Annotated[
        Path,
        typer.Option(
            "--bin-root",
            help="directory to cache binaries for some providers",
            rich_help_panel="Global Options",
        ),
    ] = state.bin_root,
    config_root: Annotated[
        Path,
        typer.Option(
            "--config-root",
            help="directory to store configuration files, e.g. legal acceptance",
            rich_help_panel="Global Options",
        ),
    ] = state.config_root,
    escape_ws: Annotated[
        bool,
        typer.Option(
            "--escape-ws",
            help="Escape newline, tab, etc. in CSV and TSV output values",
            rich_help_panel="Global Options",
        ),
    ] = state.escape_ws,
    format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format",
            rich_help_panel="Global Options",
            show_default=True,
            case_sensitive=False,
        ),
    ] = state.format,
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            "-p",
            help="Service provider to use",
            rich_help_panel="Global Options",
            show_default=True,
            case_sensitive=False,
            click_type=Choice(AVAILABLE_PROVIDERS),
        ),
    ] = state.provider,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress all stderr output except critical/fatal failures",
            rich_help_panel="Global Options",
        ),
    ] = state.quiet,
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            show_default=False,
            metavar="",
            help="Increase stderr output verbosity (can be repeated for higher levels)",
            rich_help_panel="Global Options",
        ),
    ] = 0,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show version and exit",
            rich_help_panel="Global Options",
        ),
    ] = False,
) -> None:
    """NetVelocimeter - Measuring network performance metrics across multiple service providers."""
    global state
    state.bin_root = bin_root
    state.config_root = config_root
    state.escape_ws = escape_ws
    state.format = format
    state.provider = provider
    state.quiet = quiet

    # Determine log level with precedence:
    # 1. quiet flag
    # 2. verbose count
    # 3. env var NETVELOCIMETER_LOG_LEVEL
    # 4. default level (ERROR)
    if quiet:
        log_level: int | None = logging.CRITICAL
    else:
        # Map verbosity to log levels
        log_level = {
            0: None,  # env var or default
            1: logging.WARNING,  # -v
            2: logging.INFO,  # -vv
            3: logging.DEBUG,  # -vvv
        }.get(min(verbose, 3), None)

    # Configure logger
    setup_cli_logging(log_level=log_level)

    if version:
        typer.echo(f"NetVelocimeter {version_string}")
        # quick exit with no error
        raise typer.Exit()
