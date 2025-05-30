"""Command line interface for NetVelocimeter."""

import logging
import os
from pathlib import Path
import sys
from typing import Annotated

from click import Choice
import typer

from .. import __version__ as version_string, list_providers
from ..utils.logger import get_logger, setup_logging
from ..utils.xdg import XDGCategory
from .utils.output_format import OutputFormat

# Define constants
BIN_ROOT_DEFAULT = Path(XDGCategory.BIN.resolve_path("netvelocimeter"))
CONFIG_ROOT_DEFAULT = Path(XDGCategory.CONFIG.resolve_path("netvelocimeter"))
AVAILABLE_PROVIDERS = [provider.name for provider in list_providers()]

logger: logging.Logger


class CliState:
    """State for the command line interface."""

    def __init__(self) -> None:
        """Initialize the CLI state with default values."""
        self.bin_root: Path = BIN_ROOT_DEFAULT
        self.config_root: Path = CONFIG_ROOT_DEFAULT
        self.escape_ws: bool = False
        self.format: OutputFormat = OutputFormat.TEXT
        self.provider: str = "static"  # TODO change this to ookla before publishing
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
    """Entry point for the CLI application."""
    try:
        app()
    except Exception as ex:
        # Log the exception as an error
        logger.error(str(ex))

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
            # TODO: add a list of available providers and their description to a help panel
        ),
    ] = state.provider,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress all stderr output except errors",
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
    # 3. default (WARNING)
    if quiet:
        log_level = logging.CRITICAL
    else:
        # Map verbosity to log levels
        log_level = {
            0: logging.WARNING,  # Default
            1: logging.INFO,  # -v
            2: logging.DEBUG,  # -vv
        }.get(min(verbose, 2), logging.WARNING)

    # Limit traceback display to show only on debug
    if log_level > logging.DEBUG:
        os.environ["_TYPER_STANDARD_TRACEBACK"] = "1"
        sys.tracebacklimit = 0

    # Configure logger
    setup_logging(level=log_level, force=True)
    global logger
    logger = get_logger(__name__)

    if version:
        typer.echo(f"NetVelocimeter {version_string}")
        # quick exit
        raise typer.Exit()
