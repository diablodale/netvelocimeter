"""Tests for CLI main and global options."""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
from re import escape as re_escape
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from typer.testing import CliRunner

from netvelocimeter.cli import app, entrypoint

runner = CliRunner()


def run_cli_entrypoint(argv: list[str] | None = None) -> tuple[str, str, int]:
    """Run the CLI entrypoint with the given argv-style arguments.

    This method simulates running the CLI application as if it were invoked from the command line
    in a way that allows tracking code coverage.

    Args:
        argv (list[str] | None): List of command line arguments to simulate.
            The first argument should be the command name, e.g. ["netvelocimeter", ...].
            If None, defaults to ["netvelocimeter"].

    Returns:
        tuple: A tuple containing the captured stdout, stderr, and exit code.

    Raises:
        Any: If the entrypoint raises an exception, it will be propagated.
    """
    # If no arguments are provided, use the default command
    if argv is None:
        argv = ["netvelocimeter"]

    # Patch sys.argv to simulate command line arguments
    with mock.patch.object(sys, "argv", argv):
        stdout_io = io.StringIO()
        stderr_io = io.StringIO()
        exit_code = 0
        try:
            with redirect_stdout(stdout_io), redirect_stderr(stderr_io):
                entrypoint()
        except SystemExit as e:
            exit_code = int(e.code) if e.code is not None else 0
            pass  # Typer/argparse will call sys.exit()

    # return the captured output and exit code
    return stdout_io.getvalue(), stderr_io.getvalue(), exit_code


class TestMainModule(unittest.TestCase):
    """Test cases for the main module of NetVelocimeter."""

    def test_main_module_subproc_run(self):
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
                    "-vv",
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
                    "-vv",
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

    def test_help_option(self):
        """Test that --help shows the help message."""
        result = runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("--help", result.stdout)
        self.assertIn("--version", result.stdout)
        self.assertIn("Commands", result.stdout)
        self.assertIn("Provider commands", result.stdout)

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

            # get json legal terms
            json_terms = runner.invoke(
                app,
                [
                    "--provider=static",
                    "--format=json",
                    "legal",
                    "list",
                ],
            ).stdout.strip()

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
                input=json_terms,
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
        result_error = runner.invoke(
            app,
            ["--provider=static", "legal", "list"],
        )
        result_warning = runner.invoke(
            app,
            ["--provider=static", "-v", "legal", "list"],
        )
        result_info = runner.invoke(
            app,
            ["--provider=static", "-vv", "legal", "list"],
        )
        result_debug = runner.invoke(
            app,
            ["--provider=static", "-vvv", "legal", "list"],
        )
        self.assertEqual(result_error.exit_code, 0)
        self.assertEqual(result_warning.exit_code, 0)
        self.assertEqual(result_info.exit_code, 0)
        self.assertEqual(result_debug.exit_code, 0)
        # Default mode should have no WARNING, INFO, or DEBUG logs
        self.assertNotIn("WARNING", result_error.stderr)
        self.assertNotIn("INFO", result_error.stderr)
        self.assertNotIn("DEBUG", result_error.stderr)
        # only WARNING logs should be present in warning mode
        self.assertIn("WARNING", result_warning.stderr)
        self.assertNotIn("INFO", result_warning.stderr)
        self.assertNotIn("DEBUG", result_warning.stderr)
        # only WARNING and INFO logs should be present in info mode
        self.assertIn("WARNING", result_info.stderr)
        self.assertIn("INFO", result_info.stderr)
        self.assertNotIn("DEBUG", result_info.stderr)
        # WARNING, INFO, and DEBUG logs should be present in debug mode
        self.assertIn("WARNING", result_debug.stderr)
        self.assertIn("INFO", result_debug.stderr)
        self.assertIn("DEBUG", result_debug.stderr)

    def test_version_option(self):
        """Test --version outputs the version and exits."""
        from netvelocimeter import __version__ as version_string

        result = runner.invoke(app, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout, f"NetVelocimeter {version_string}\n")

    def test_bad_option(self):
        """Test that an invalid option raises an error."""
        result = runner.invoke(app, ["--invalid-option"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such option", result.stderr)

    def test_bad_command(self):
        """Test that an invalid command raises an error."""
        result = runner.invoke(app, ["invalid-command"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such command", result.stderr)

    def test_internal_exception_gets_logged(self):
        """Test that an internal exception gets logged."""
        test_args = ["netvelocimeter", "--config-root", "\\#INVALID:/invalid", "legal", "list"]
        with self.assertLogs(logger=None, level="CRITICAL") as log:
            stdout, stderr, exit_code = run_cli_entrypoint(test_args)

        # Verify log content
        self.assertNotEqual(exit_code, 0)
        self.assertEqual(len(log.records), 1)
        self.assertEqual(log.records[0].levelname, "CRITICAL")
        self.assertRegex(
            log.output[0],
            r"(?i)(invalid|file|directory|volume|path)",
        )
        self.assertNotIn("Traceback", log.output[0])
        self.assertNotIn("Traceback", stdout)
        self.assertNotIn("Traceback", stderr)

    def test_internal_exception_gets_logged_and_rethrown(self):
        """Test that an internal exception with debug log gets logged and rethrown."""
        test_args = [
            "netvelocimeter",
            "-vvv",
            "--config-root",
            "\\#INVALID:/invalid",
            "legal",
            "list",
        ]
        with (
            self.assertRaises(Exception) as context,
            self.assertLogs(logger=None, level="CRITICAL") as log,
        ):
            stdout, stderr, exit_code = run_cli_entrypoint(test_args)

        # Verify log content
        self.assertEqual(len(log.records), 1)
        self.assertEqual(log.records[0].levelname, "CRITICAL")
        self.assertRegex(
            log.output[0],
            r"(?i)(invalid|file|directory|volume|path)",
        )

        # Verify that the bad path exception was raised
        self.assertRegex(
            str(context.exception),
            r"(?i)(invalid|file|directory|volume|path)",
        )
