"""Tests for CLI server command."""

import unittest

from typer.testing import CliRunner

from netvelocimeter.cli import app

runner = CliRunner(mix_stderr=False)


class TestServerCommand(unittest.TestCase):
    """Test cases for the CLI server command."""

    def test_server_list_success(self):
        """Test 'server list' outputs available servers for static provider."""
        result = runner.invoke(app, ["--provider=static", "server", "list"])
        self.assertEqual(result.exit_code, 0)
        # Should contain all 5 test static servers
        for i in range(1, 6):
            self.assertRegex(
                result.stdout,
                f"name:\\s+Test Server {i}\nid:\\s+{i}\nhost:\\s+test{i}.example.com\n"
                f"location:\\s+Test Location {i}\ncountry:\\s+Test Country\n",
            )

    def test_server_list_help(self):
        """Test 'server list --help' outputs usage."""
        result = runner.invoke(app, ["server", "list", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stdout, r"List servers(.|\n)+Show this message")
