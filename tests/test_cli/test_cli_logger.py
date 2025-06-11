"""Tests for the CLI logger."""

import io
import logging
import os
import unittest
from unittest import mock

from netvelocimeter.cli.utils.logger import setup_cli_logging


class TestLogger(unittest.TestCase):
    """Test cases for the logger module."""

    def setUp(self):
        """Save the original handlers and level for the netvelocimeter logger."""
        self.logger = logging.getLogger("netvelocimeter")
        self._orig_handlers = self.logger.handlers[:]
        self._orig_level = self.logger.level

    def tearDown(self):
        """Restore the original handlers and level for the netvelocimeter logger."""
        self.logger.handlers = self._orig_handlers
        self.logger.setLevel(self._orig_level)

    def test_setup_cli_logging_configures_root_logger(self):
        """Test setup_cli_logging configures the netvelocimeter logger for CLI."""
        setup_cli_logging(log_level=logging.INFO)
        root_logger = logging.getLogger("netvelocimeter")
        self.assertEqual(root_logger.level, logging.INFO)
        self.assertTrue(any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers))

        # Verify log content
        with self.assertLogs(logger="netvelocimeter", level="INFO") as log:
            root_logger.info("Test log message")
        self.assertEqual(len(log.records), 1)
        self.assertEqual(log.records[0].levelname, "INFO")
        self.assertIn("Test log message", log.output[0])

    def test_setup_cli_logging_respects_env_variable(self):
        """Test setup_cli_logging respects NETVELOCIMETER_LOG_LEVEL env variable."""
        with mock.patch.dict(os.environ, {"NETVELOCIMETER_LOG_LEVEL": "INFO"}):
            setup_cli_logging()
            root_logger = logging.getLogger("netvelocimeter")
            self.assertEqual(root_logger.level, logging.INFO)

    def test_setup_cli_logging_invalid_env_level(self):
        """Test setup_cli_logging falls back to ERROR on invalid env variable."""
        with (
            mock.patch.dict(os.environ, {"NETVELOCIMETER_LOG_LEVEL": "INVALID"}),
            mock.patch("logging.Logger.error") as mock_error,
        ):
            setup_cli_logging()
            root_logger = logging.getLogger("netvelocimeter")
            self.assertEqual(root_logger.level, logging.ERROR)
            mock_error.assert_called_once()

    def test_log_format_and_utc(self):
        """Test log message format and UTC timestamp."""
        # Ensure CLI logging is configured with the real handler/formatter
        setup_cli_logging(log_level=logging.DEBUG)
        logger = logging.getLogger("netvelocimeter")

        # Find the first StreamHandler attached by setup_cli_logging
        stream_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                stream_handler = handler
                break
        self.assertIsNotNone(stream_handler, "No StreamHandler found on netvelocimeter root logger")

        # Save the original stream to restore later to avoid side effects
        original_stream = stream_handler.stream

        # Swap the handler's stream to a StringIO to capture output, preserving formatter
        log_buffer = io.StringIO()
        stream_handler.stream = log_buffer

        try:
            # Log a test message
            logger.debug("Test message")
            log_output = log_buffer.getvalue().strip()

            # Check format
            self.assertRegex(
                log_output,
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z \[DEBUG\] netvelocimeter: Test message$",
            )
        finally:
            # Restore the original stream to avoid side effects
            stream_handler.stream = original_stream
