"""Tests for the logger module using unittest methodology."""

import logging
import os
import time
import unittest
from unittest import mock

from netvelocimeter.utils.logger import ROOT_LOGGER_NAME, get_logger, setup_logging


class TestLogger(unittest.TestCase):
    """Test cases for the logger module."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        from netvelocimeter.utils.logger import root_logger

        # Store original handlers and level
        self.original_handlers = list(root_logger.handlers)
        self.original_level = root_logger.level

        # Remove all handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        from netvelocimeter.utils.logger import root_logger

        # Restore original state after test
        root_logger.setLevel(self.original_level)
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        for handler in self.original_handlers:
            root_logger.addHandler(handler)

    def test_get_logger_returns_correct_logger(self):
        """Test that get_logger returns correctly named loggers."""
        # Test component logger
        component_logger = get_logger("test_component")
        self.assertEqual(component_logger.name, f"{ROOT_LOGGER_NAME}.test_component")

        # Test root logger
        root_logger = get_logger(ROOT_LOGGER_NAME)
        self.assertEqual(root_logger.name, ROOT_LOGGER_NAME)

    def test_logger_hierarchy(self):
        """Test that loggers maintain proper hierarchy."""
        parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")

        # Child should inherit from parent
        self.assertEqual(parent_logger.name, f"{ROOT_LOGGER_NAME}.parent")
        self.assertEqual(child_logger.name, f"{ROOT_LOGGER_NAME}.parent.child")

    def test_setup_logging_with_different_levels(self):
        """Test setup_logging with different log levels."""
        from netvelocimeter.utils.logger import root_logger

        # Test cases: (level_input, expected_level)
        test_cases = [
            (logging.DEBUG, logging.DEBUG),
            (logging.INFO, logging.INFO),
            (logging.WARNING, logging.WARNING),
            (logging.ERROR, logging.ERROR),
            (logging.CRITICAL, logging.CRITICAL),
            (None, logging.WARNING),  # Default level
        ]

        for level_input, expected_level in test_cases:
            with self.subTest(
                level=logging.getLevelName(expected_level if expected_level else logging.WARNING)
            ):
                setup_logging(level=level_input, force=True)
                self.assertEqual(root_logger.level, expected_level)

    def test_setup_logging_with_environment_variable(self):
        """Test setup_logging respects environment variable."""
        from netvelocimeter.utils.logger import root_logger

        # Test with valid level
        with mock.patch.dict(os.environ, {"NETVELOCIMETER_LOG_LEVEL": "ERROR"}):
            setup_logging(force=True)
            self.assertEqual(root_logger.level, logging.ERROR)

        # Test with invalid level
        with mock.patch.dict(os.environ, {"NETVELOCIMETER_LOG_LEVEL": "INVALID"}):
            # Add a handler to test warning message
            handler = logging.StreamHandler()
            root_logger.addHandler(handler)

            with mock.patch.object(root_logger, "warning") as mock_warning:
                setup_logging(force=True)
                mock_warning.assert_called_once()
                self.assertIn("Invalid environment log level", mock_warning.call_args[0][0])

            self.assertEqual(root_logger.level, logging.WARNING)

    def test_setup_logging_handler_creation(self):
        """Test that setup_logging creates a handler when needed."""
        from netvelocimeter.utils.logger import root_logger

        # Logger should have no handlers initially
        self.assertEqual(len(root_logger.handlers), 0)

        # Setup should add a handler
        setup_logging()
        self.assertEqual(len(root_logger.handlers), 1)
        self.assertIsInstance(root_logger.handlers[0], logging.StreamHandler)

        # Second call shouldn't add another handler
        setup_logging()
        self.assertEqual(len(root_logger.handlers), 1)

    def test_setup_logging_force_parameter(self):
        """Test that force=True reconfigures existing loggers."""
        from netvelocimeter.utils.logger import root_logger

        # Initial setup
        setup_logging(level=logging.INFO)
        self.assertEqual(root_logger.level, logging.INFO)
        self.assertEqual(len(root_logger.handlers), 1)

        # Without force, level shouldn't change
        setup_logging(level=logging.DEBUG)
        self.assertEqual(root_logger.level, logging.INFO)

        # With force, level should change
        setup_logging(level=logging.DEBUG, force=True)
        self.assertEqual(root_logger.level, logging.DEBUG)

    def test_logger_format(self):
        """Test that log messages are properly formatted."""
        import io

        from netvelocimeter.utils.logger import root_logger

        # Set up a string buffer to capture log output
        log_buffer = io.StringIO()
        handler = logging.StreamHandler(log_buffer)

        # Create formatter with a fixed time for testing
        formatter = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03dZ [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

        # Use a fixed time tuple (2023-01-01 12:00:00 UTC)
        fixed_time = time.struct_time((2023, 1, 1, 12, 0, 0, 0, 0, 0))
        formatter.converter = lambda *args: fixed_time

        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

        # Log a test message
        root_logger.warning("Test message")

        # Check format
        log_output = log_buffer.getvalue()
        self.assertIn("[WARNING]", log_output)
        self.assertIn("Test message", log_output)
        self.assertIn(f"{ROOT_LOGGER_NAME}:", log_output)

    def test_logging_integration(self):
        """Test integration with core module."""
        # Import logger from core
        with mock.patch("netvelocimeter.core.logger.warning") as mock_warning:
            # Trigger code that logs in core
            from netvelocimeter.core import NetVelocimeter

            # Creating with unsupported parameter should log
            NetVelocimeter(unknown_param="test")

            # Verify core logging occurred with expected message
            mock_warning.assert_called_once()
            self.assertIn("does not support parameters", mock_warning.call_args[0][0])
            self.assertIn("unknown_param", str(mock_warning.call_args))

    def test_formatter_timezone_is_utc(self):
        """Test that timestamps are in UTC."""
        from netvelocimeter.utils.logger import root_logger

        setup_logging(force=True)

        # Get the formatter
        handler = root_logger.handlers[0]
        formatter = handler.formatter

        # Check that converter is set to gmtime
        self.assertEqual(formatter.converter, time.gmtime)
