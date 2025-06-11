"""Logging configuration for NetVelocimeter CLI."""

import logging
import os
import sys
import time


def setup_cli_logging(
    log_level: int | None = None,
) -> None:
    """Configure the root logger for NetVelocimeter CLI.

    The log level is set through a cascade of options:
    1. `log_level` parameter (if provided).
    2. `NETVELOCIMETER_LOG_LEVEL` environment variable (if set).
    3. `logging.ERROR` default.

    Args:
        log_level: Numeric log level override (logging.DEBUG, logging.INFO, etc.)
    """
    # get root logger
    root_logger = logging.getLogger("netvelocimeter")

    # Add console handler
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03dZ [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    # Convert timestamps to UTC
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)

    # remove existing handlers and add the new one
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Set root log level based on parameter, env var, or default
    if log_level is None:
        # Try to get from environment variable
        env_level_name = os.environ.get("NETVELOCIMETER_LOG_LEVEL", "").upper()
        if env_level_name:
            try:
                log_level = getattr(logging, env_level_name)
            except AttributeError:
                root_logger.error(
                    f"Invalid NETVELOCIMETER_LOG_LEVEL '{env_level_name}', using ERROR."
                )

    # Set level on root logger, defaulting to ERROR if not specified
    log_level = log_level or logging.ERROR
    root_logger.setLevel(log_level)

    # Limit traceback display to show only on debug and more verbose levels
    if log_level > logging.DEBUG:
        os.environ["_TYPER_STANDARD_TRACEBACK"] = "1"
        sys.tracebacklimit = 0
