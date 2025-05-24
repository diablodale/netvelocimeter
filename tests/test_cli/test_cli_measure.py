"""Tests for CLI measure command."""

import unittest

from typer.testing import CliRunner

from netvelocimeter.cli.main import app

runner = CliRunner(mix_stderr=False)


class TestMeasureCommand(unittest.TestCase):
    """Test cases for the CLI measure command."""

    def test_app(self):
        """Test the CLI app with a simple command."""
        result = runner.invoke(app, ["-vv", "--provider=static", "measure", "run"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("download_latency: 30.00 ms", result.stdout)
        # TODO better and more tests
