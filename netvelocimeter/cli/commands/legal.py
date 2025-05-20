"""Legal commands for the NetVelocimeter CLI."""

from typing import Annotated

import typer
from typer import Typer

from ... import NetVelocimeter
from ...terms import LegalTermsCategory, LegalTermsCategoryCollection
from ...utils.logger import get_logger
from ..main import state
from ..utils.formatters import format_records

# Get logger for legal commands
logger = get_logger("cli.legal")

# Create legal command group
legal_app = Typer(
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,  # hinder disclosing secrets
    help="Legal commands",
)


def register_legal_commands(app: Typer) -> None:
    """Register legal commands with the main app."""
    app.add_typer(legal_app, name="legal")


@legal_app.command(name="list")
def legal_list(
    category: Annotated[
        LegalTermsCategoryCollection,
        typer.Option(
            "--category",
            "-c",
            help="Category filter",
            case_sensitive=False,
        ),
        # typer.Argument(
        #    help="Category filter",
        #    case_sensitive=False,
        #    # workaround typer bug in usage and help panel for enum arguments
        #    metavar=f"[{'|'.join(LegalTermsCategory.__members__.values())}]",
        # ),
    ] = [LegalTermsCategory.ALL],  # noqa: B006
) -> None:
    """Legal terms for the selected provider."""
    logger.info(
        f"Listing legal terms for provider '{state['provider']}' with category filter {category}"
    )

    nv = NetVelocimeter(
        provider=state["provider"],
        bin_root=state["bin_root"],
        config_root=state["config_root"],
    )

    # Get the list of legal terms
    legal_terms = nv.legal_terms(category)
    logger.debug(
        f"Provider '{state['provider']}' has {len(legal_terms)} legal terms after filter '{category}'"
    )
    typer.echo(format_records(legal_terms, state["format"]) if legal_terms else "No legal terms.")
