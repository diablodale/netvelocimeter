"""Tests for CLI server command."""

from tempfile import TemporaryDirectory
import unittest

from typer.testing import CliRunner

from netvelocimeter.cli import app

runner = CliRunner()


class TestServerCommand(unittest.TestCase):
    """Test cases for the CLI server command."""

    def test_server_list_success(self):
        """Test 'server list' outputs available servers for static provider."""
        with TemporaryDirectory() as temp_dir:
            # get all terms
            result = runner.invoke(
                app,
                ["--config-root", temp_dir, "--format=json", "--provider=static", "legal", "list"],
            )
            self.assertEqual(result.exit_code, 0)

            # accept all terms
            result = runner.invoke(
                app,
                ["--config-root", temp_dir, "--provider=static", "legal", "accept"],
                input=result.stdout,
            )
            self.assertEqual(result.exit_code, 0)

            # list servers
            result = runner.invoke(
                app, ["--config-root", temp_dir, "--provider=static", "server", "list"]
            )
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
