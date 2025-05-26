"""Legal commands for the NetVelocimeter CLI."""

import sys
from typing import Annotated

import typer
from typer import Typer

from ... import NetVelocimeter
from ...legal import LegalTerms, LegalTermsCategory, LegalTermsCategoryCollection
from ...utils.logger import get_logger
from ..main import state
from ..utils.formatters import format_records

# Get logger for legal commands
logger = get_logger(__name__)

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


@legal_app.command(name="accept")
def legal_accept() -> None:
    """Accept legal terms (JSON only) from stdin for the selected provider."""
    logger.info("Reading legal terms from stdin")
    terms_json = sys.stdin.read().strip()

    if not terms_json:
        logger.error("No legal terms provided. Exiting.")
        raise typer.Exit(code=1)

    nv = NetVelocimeter(
        provider=state.provider,
        bin_root=state.bin_root,
        config_root=state.config_root,
    )
    try:
        # Parse the JSON input
        logger.debug(f"Parsing legal terms JSON: {terms_json}")
        terms_to_accept = LegalTerms.from_json(terms_json)
        if isinstance(terms_to_accept, LegalTerms):
            terms_to_accept = [terms_to_accept]
        logger.debug(f"Parsed {len(terms_to_accept)} legal terms")

        # Accept the parsed terms
        nv.accept_terms(terms_to_accept)
        logger.info(f"Accepted {len(terms_to_accept)} legal terms")

    except Exception as e:
        logger.error(f"Error accepting legal terms: {e}")
        raise typer.Exit(code=1) from e


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
    """List legal terms for the selected provider."""
    logger.info(
        f"Listing legal terms for provider '{state.provider}' with category filter {category}"
    )

    nv = NetVelocimeter(
        provider=state.provider,
        bin_root=state.bin_root,
        config_root=state.config_root,
    )

    # Get the list of legal terms
    terms = nv.legal_terms(category)
    logger.debug(
        f"Provider '{state.provider}' has {len(terms)} legal terms after filter '{category}'"
    )

    # Display the legal terms
    if terms:
        typer.echo(format_records(terms, state.format, state.escape_ws))
    else:
        logger.warning("No results.")


@legal_app.command(name="status")
def legal_status(
    categories: Annotated[
        list[LegalTermsCategory],
        typer.Option(
            "--category",
            "-c",
            help="Category filter",
            case_sensitive=False,
        ),
    ] = [LegalTermsCategory.ALL],  # noqa: B006
) -> None:
    """Status for acceptance of legal terms for the selected provider."""
    nv = NetVelocimeter(
        provider=state.provider,
        bin_root=state.bin_root,
        config_root=state.config_root,
    )

    # Check if terms are accepted
    terms = nv.legal_terms(categories)
    logger.debug(
        f"Provider '{state.provider}' has {len(terms)} legal terms after filter '{categories}'"
    )
    for term in terms:
        term.accepted = nv.has_accepted_terms(term)

    # Display the status of legal terms
    if terms:
        typer.echo(format_records(terms, state.format, state.escape_ws))
    else:
        logger.warning("No results.")

    # exit with success if all terms are accepted
    if all(term.accepted for term in terms):
        logger.info("All filtered legal terms accepted.")
        raise typer.Exit(code=0)
    else:
        logger.info("Not all filtered legal terms accepted.")
        raise typer.Exit(code=1)
