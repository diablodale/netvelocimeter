"""Command line interface for NetVelocimeter."""

from enum import Enum
import os
from pathlib import Path
import sys
from typing import Annotated, TypedDict

from click import Choice
import typer

from . import NetVelocimeter, list_providers
from .utils.xdg import XDGCategory


class OutputFormat(str, Enum):
    """Output format for the command line interface."""

    TEXT = "text"
    CSV = "csv"
    TSV = "tsv"
    JSON = "json"


class CliState(TypedDict):
    """State for the command line interface."""

    bin_root: Path
    config_root: Path
    format: OutputFormat
    provider: str


# Define constants
BIN_ROOT_DEFAULT = Path(XDGCategory.BIN.resolve_path("netvelocimeter"))
CONFIG_ROOT_DEFAULT = Path(XDGCategory.CONFIG.resolve_path("netvelocimeter"))
AVAILABLE_PROVIDERS = [provider.name for provider in list_providers()]

# Running in a PyInstaller bundle
# IN_PYINSTALL_BUNDLE = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# state container and defaults
state: CliState = {
    "bin_root": BIN_ROOT_DEFAULT,
    "config_root": CONFIG_ROOT_DEFAULT,
    "format": OutputFormat.TEXT,
    "provider": "static",
}

#########################
#### Global Commands ####
#########################

# Define the Typer app
app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,  # hinder disclosing secrets
)


@app.callback(invoke_without_command=True)
def main(
    bin_root: Annotated[
        Path,
        typer.Option(
            "--bin-root",
            help="directory to cache binaries for some providers",
        ),
    ] = state["bin_root"],
    config_root: Annotated[
        Path,
        typer.Option(
            "--config-root",
            help="directory to store configuration files, e.g. legal acceptance",
        ),
    ] = state["config_root"],
    format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            help="Output format",
            show_default=True,
            case_sensitive=False,
        ),
    ] = state["format"],
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            help="Service provider to use",
            show_default=True,
            case_sensitive=False,
            click_type=Choice(AVAILABLE_PROVIDERS),
            # TODO: add a list of available providers and their description to a help panel
        ),
    ] = state["provider"],
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Make the output more verbose",
            is_eager=True,
        ),
    ] = False,
    version: Annotated[bool, typer.Option("--version", help="Show version and exit")] = False,
) -> None:
    """NetVelocimeter - Measuring network performance metrics across multiple service providers."""
    global state
    state["bin_root"] = bin_root
    state["config_root"] = config_root
    state["format"] = format
    state["provider"] = provider
    if not verbose:
        os.environ["_TYPER_STANDARD_TRACEBACK"] = "1"
        sys.tracebacklimit = 0
    if version:
        version_str = NetVelocimeter.library_version()
        typer.echo(f"NetVelocimeter {version_str}")
        raise typer.Exit()


#########################
#### Server Commands ####
#########################

# Define the typer app for server commands
server_app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,  # hinder disclosing secrets
    help="Server commands",
)
app.add_typer(server_app, name="server")


@server_app.command(name="list")
def server_list() -> None:
    """List servers for the selected provider."""
    nv = NetVelocimeter(
        provider=state["provider"],
        bin_root=state["bin_root"],
        config_root=state["config_root"],
    )
    # BUGBUG remove auto accept
    nv.accept_terms(nv.legal_terms())

    # get the list of servers
    servers = nv.servers
    if not servers:
        typer.echo("No servers available for the selected provider.")
        raise typer.Exit(code=1)

    # print the list of servers
    if state["format"] == OutputFormat.TEXT:
        for server in servers:
            # BUGBUG remove extra newlines and dyamically output fields
            typer.echo(f"Name: {server.name}")
            if server.id:
                typer.echo(f"Id: {server.id}")
            if server.host:
                typer.echo(f"Host: {server.host}")
            if server.location:
                typer.echo(f"Location: {server.location}")
            if server.country:
                typer.echo(f"Country: {server.country}")
            typer.echo()

    elif state["format"] == OutputFormat.CSV or state["format"] == OutputFormat.TSV:
        import csv
        from io import StringIO

        # get all class dict keys from the first server class object, remove the "raw" field
        field_names = [key for key in servers[0].to_dict() if key != "raw"]

        # write the header
        csv_output = StringIO()
        writer = csv.DictWriter(
            f=csv_output,
            fieldnames=field_names,
            extrasaction="ignore",
            dialect="unix" if state["format"] == OutputFormat.CSV else "excel-tab",
            lineterminator="\n",
        )
        writer.writeheader()

        # write the server data
        for server in servers:
            # convert the server object to a dictionary
            writer.writerow(server.to_dict())

        # print the CSV output
        typer.echo(csv_output.getvalue())

    elif state["format"] == OutputFormat.JSON:
        import json

        json_data = [server.to_dict() for server in servers]
        typer.echo(json.dumps(json_data, indent=2))

    else:
        # This indicates a programming error - all enum values should be handled
        raise NotImplementedError(
            f"DEVELOPER ERROR: Format {state['format']} is defined in OutputFormat enum "
            "but no output handler is implemented!"
        )


if __name__ == "__main__":
    app()


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
