"""Tests for CLI measure command."""

import shutil
import tempfile
import unittest

from typer.testing import CliRunner

from netvelocimeter.cli import app

runner = CliRunner(mix_stderr=False)

# The static provider always returns these legal terms
STATIC_TERMS = r"""
[
    {
        "text": "Test EULA",
        "category": "eula",
        "url": "https://example.com/eula"
    },
    {
        "text": "Test Privacy",
        "category": "privacy",
        "url": "https://example.com/privacy"
    },
    {
        "text": "Test Terms",
        "category": "service",
        "url": "https://example.com/terms"
    }
]
"""


class TestMeasureCommand(unittest.TestCase):
    """Test cases for the CLI measure command."""

    def setUp(self):
        """Set up the test environment."""
        # Create a temp config dir for isolation
        self.temp_dir = tempfile.mkdtemp()

        # Accept all static legal terms so measure can run
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "--config-root",
                self.temp_dir,
                "legal",
                "accept",
            ],
            input=STATIC_TERMS,
        )
        self.assertEqual(result.exit_code, 0)

    def tearDown(self):
        """Clean up the test environment."""
        shutil.rmtree(self.temp_dir)

    def test_measure_run_basic(self):
        """Test measure run with static provider."""
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "--config-root",
                self.temp_dir,
                "measure",
                "run",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stdout, r"download_latency:\s+30.00 ms")
        self.assertRegex(result.stdout, r"upload_latency:\s+60.00 ms")
        self.assertRegex(result.stdout, r"ping_latency:\s+25.00 ms")
        self.assertRegex(result.stdout, r"packet_loss:\s+1.30 %")
        self.assertRegex(result.stdout, r"download_speed:")
        self.assertRegex(result.stdout, r"upload_speed:")
        self.assertRegex(result.stdout, r"server_name:\s+Test Server 1")

    def test_measure_run_repeat(self):
        """Test running measure multiple times (should always succeed)."""
        for _ in range(3):
            result = runner.invoke(
                app,
                [
                    "--provider=static",
                    "--config-root",
                    self.temp_dir,
                    "measure",
                    "run",
                ],
            )
            self.assertEqual(result.exit_code, 0)
            self.assertRegex(result.stdout, r"download_latency:\s+30.00 ms")

    def test_measure_run_help(self):
        """Test measure run --help outputs usage."""
        result = runner.invoke(app, ["measure", "run", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Run a measurement", result.stdout)

    def test_measure_run_with_verbose_verbose(self):
        """Test measure run with verbose verbose (debug) flag."""
        result = runner.invoke(
            app,
            [
                "-vv",
                "--provider=static",
                "--config-root",
                self.temp_dir,
                "measure",
                "run",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("download_latency: 30.00 ms", result.stdout)
        self.assertIn("DEBUG", result.stderr)

    def test_measure_run_without_accepting_terms(self):
        """Test measure run fails if legal terms are not accepted."""
        # New temp dir, do not accept terms
        with tempfile.TemporaryDirectory() as temp_dir2:
            result = runner.invoke(
                app,
                [
                    "--provider=static",
                    "--config-root",
                    temp_dir2,
                    "measure",
                    "run",
                ],
            )
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("must accept all legal terms", str(result.exception).lower())

    def test_measure_run_output_contains_server_info(self):
        """Test that server info fields are present in output."""
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "--config-root",
                self.temp_dir,
                "measure",
                "run",
            ],
        )
        self.assertIn("server_name:", result.stdout.lower())
        self.assertIn("server_host:", result.stdout.lower())
        self.assertIn("server_country:", result.stdout.lower())

    def test_measure_run_exit_code(self):
        """Test that measure run returns exit code 0 on success."""
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "--config-root",
                self.temp_dir,
                "measure",
                "run",
            ],
        )
        self.assertEqual(result.exit_code, 0)
