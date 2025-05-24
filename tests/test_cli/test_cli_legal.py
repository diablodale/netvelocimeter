"""Tests for CLI legal command."""

import unittest

from typer.testing import CliRunner

from netvelocimeter.cli.main import app

runner = CliRunner(mix_stderr=False)


class TestLegalCommand(unittest.TestCase):
    """Test cases for the CLI legal command."""

    def test_cli_legal_list(self):
        """Test the CLI app with a simple command."""
        result = runner.invoke(app, ["-vv", "--provider=static", "legal", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("category: eula", result.stdout)
        self.assertIn("category: privacy", result.stdout)
        self.assertIn("category: service", result.stdout)
        # TODO better and more tests
