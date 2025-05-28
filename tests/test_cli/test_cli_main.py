"""Tests for CLI main and global options."""

from pathlib import Path
from re import escape as re_escape
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from typer.testing import CliRunner

from netvelocimeter.cli import app

runner = CliRunner(mix_stderr=False)

# get json legal terms once
JSON_TERMS = runner.invoke(
    app,
    [
        "--provider=static",
        "--format=json",
        "legal",
        "list",
    ],
).stdout.strip()


class TestMainModule(unittest.TestCase):
    """Test cases for the main module of NetVelocimeter."""

    def test_main_module_runs(self):
        """Test that the main module can be run as a script."""
        pkg_dir = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "netvelocimeter", "--help"],
            cwd=str(pkg_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
        )
        self.assertEqual(result.returncode, 0)
        self.assertRegex(
            result.stdout, r"Usage:(.|\n)+--help(.|\n)+--config-root(.|\n)+--version(.|\n)+server"
        )

    def test_bin_root_option(self):
        """Test --bin-root sets the binary root directory and CLI still works."""
        with TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                app,
                [
                    "--provider=static",
                    "--bin-root",
                    temp_dir,
                    "-v",
                    "legal",
                    "list",
                ],
            )
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stderr, f"INFO.+Binary cache at {re_escape(temp_dir)}")

    def test_config_root_option(self):
        """Test --config-root sets the config root directory and CLI still works."""
        with TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                app,
                [
                    "--provider=static",
                    "--config-root",
                    temp_dir,
                    "-v",
                    "legal",
                    "list",
                ],
            )
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stderr, f"INFO.+Legal terms tracking at {re_escape(temp_dir)}")

    def test_escape_ws_option(self):
        """Test --escape-ws affects output (should escape whitespace if present)."""
        result = runner.invoke(
            app,
            [
                "--escape-ws",
                "--format=csv",
                "provider",
                "list",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stdout, r'(?m)^"static"[^\n]+Five test servers')
        self.assertNotRegex(result.stdout, r"(?m)^Five test servers")

    def test_format_text_option(self):
        """Test --format text outputs pretty column text."""
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "--format=text",
                "legal",
                "list",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stdout, r"(?m)^category:\s+service\ntext:\s+Test Terms$")

    def test_format_csv_option(self):
        """Test --format csv outputs CSV."""
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "--format=csv",
                "legal",
                "list",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.stdout.startswith('"category","text","url"'))
        self.assertIn('"eula","Test EULA","https://example.com/eula"', result.stdout)

    def test_format_tsv_option(self):
        """Test --format tsv outputs TSV."""
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "--format=tsv",
                "legal",
                "list",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.stdout.startswith("category\ttext\turl"))
        self.assertIn("eula\tTest EULA\thttps://example.com/eula", result.stdout)

    def test_format_json_option(self):
        """Test --format json outputs JSON."""
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "--format=json",
                "legal",
                "list",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        stripped_output = result.stdout.strip()
        self.assertTrue(stripped_output.startswith("["))
        self.assertTrue(stripped_output.endswith("]"))

    def test_provider_option(self):
        """Test --provider option selects the provider."""
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "legal",
                "list",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Test EULA", result.stdout)

        # Test with an invalid provider
        result_invalid = runner.invoke(
            app,
            [
                "--provider=invalid_provider",
                "legal",
                "list",
            ],
        )
        self.assertNotEqual(result_invalid.exit_code, 0)
        self.assertIn("Invalid value for '--provider'", result_invalid.stderr)

    def test_quiet_option(self):
        """Test --quiet sets log level to ERROR and suppresses info/warning."""
        with TemporaryDirectory() as temp_dir:
            # Check if terms are accepted, should not be accepted yet
            result = runner.invoke(
                app,
                [
                    "--provider=static",
                    "--config-root",
                    temp_dir,
                    "--quiet",
                    "legal",
                    "status",
                ],
            )
            # Ensure the command returns non-zero exit code
            self.assertNotEqual(result.exit_code, 0)
            # Should not have any output
            self.assertFalse(result.stdout)
            self.assertFalse(result.stderr)
            self.assertRaises(SystemExit)

            # Accept all static legal terms
            result = runner.invoke(
                app,
                [
                    "--provider=static",
                    "--config-root",
                    temp_dir,
                    "--quiet",
                    "legal",
                    "accept",
                ],
                input=JSON_TERMS,
            )
            # Ensure the command returns zero exit code
            self.assertEqual(result.exit_code, 0)
            # Should not have any output
            self.assertFalse(result.stdout)
            self.assertFalse(result.stderr)
            self.assertFalse(result.exception)

            # Check if terms are accepted, should be accepted now
            result = runner.invoke(
                app,
                [
                    "--provider=static",
                    "--config-root",
                    temp_dir,
                    "--quiet",
                    "legal",
                    "status",
                ],
            )
            # Ensure the command returns zero exit code
            self.assertEqual(result.exit_code, 0)
            # Should not have any output
            self.assertFalse(result.stdout)
            self.assertFalse(result.stderr)
            self.assertFalse(result.exception)

    def test_verbose_option(self):
        """Test -v and -vv increase verbosity."""
        result_default = runner.invoke(
            app,
            ["--provider=static", "legal", "list"],
        )
        result_info = runner.invoke(
            app,
            ["--provider=static", "-v", "legal", "list"],
        )
        result_debug = runner.invoke(
            app,
            ["--provider=static", "-vv", "legal", "list"],
        )
        self.assertEqual(result_default.exit_code, 0)
        self.assertEqual(result_info.exit_code, 0)
        self.assertEqual(result_debug.exit_code, 0)
        # Default mode should have no INFO or DEBUG logs
        self.assertNotIn("INFO", result_default.stderr)
        self.assertNotIn("DEBUG", result_default.stderr)
        # only INFO logs should be present in info mode
        self.assertIn("INFO", result_info.stderr)
        self.assertNotIn("DEBUG", result_info.stderr)
        # INFO and DEBUG logs should be present in debug mode
        self.assertIn("INFO", result_debug.stderr)
        self.assertIn("DEBUG", result_debug.stderr)

    def test_version_option(self):
        """Test --version outputs the version and exits."""
        from netvelocimeter import __version__ as version_string

        result = runner.invoke(app, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout, f"NetVelocimeter {version_string}\n")
