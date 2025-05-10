"""Logging configuration for NetVelocimeter."""

import logging
import os
import sys
import time

# Constants
ROOT_LOGGER_NAME = "netvelocimeter"
_DEFAULT_LOG_LEVEL = logging.WARNING

# Create root logger
_root_logger = logging.getLogger(ROOT_LOGGER_NAME)


def setup_logging(
    level: int | None = None,
    force: bool = False,
) -> None:
    """Configure the root logger for NetVelocimeter.

    The log level is set through a cascade of options:
    1. `level` parameter (if provided).
    2. `NETVELOCIMETER_LOG_LEVEL` environment variable (if set).
    3. Default WARNING level.

    Args:
        level: Numeric log level override (logging.DEBUG, logging.INFO, etc.)
        force: Force reconfiguration even if already configured
    """
    # Skip if already configured unless forced
    if not force and _root_logger.handlers:
        return

    # Set level based on parameter, environment, or default
    numeric_level = level
    if numeric_level is None:
        # Try to get from environment variable
        env_level_name = os.environ.get("NETVELOCIMETER_LOG_LEVEL", "").upper()
        if env_level_name:
            try:
                numeric_level = getattr(logging, env_level_name)
            except AttributeError:
                # Invalid level name, use default
                # Can't log a warning yet if no handler is set up
                if _root_logger.handlers:
                    _root_logger.warning(
                        f"Invalid environment log level '{env_level_name}', using default"
                    )
                numeric_level = _DEFAULT_LOG_LEVEL
        else:
            # No env var, use default
            numeric_level = _DEFAULT_LOG_LEVEL

    # Set level on root logger
    _root_logger.setLevel(numeric_level)

    # Clear existing handlers if forcing
    if force:
        for handler in _root_logger.handlers:
            _root_logger.removeHandler(handler)

    # Add console handler if needed
    if not _root_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03dZ [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        # Convert timestamps to UTC
        formatter.converter = time.gmtime
        handler.setFormatter(formatter)
        _root_logger.addHandler(handler)


def get_logger(name: str = ROOT_LOGGER_NAME) -> logging.Logger:
    """Get a logger for a component.

    Args:
        name: Component name (e.g., "core", "providers")

    Returns:
        Configured logger instance
    """
    setup_logging()
    return logging.getLogger(
        f"{ROOT_LOGGER_NAME}.{name}" if name != ROOT_LOGGER_NAME else ROOT_LOGGER_NAME
    )
