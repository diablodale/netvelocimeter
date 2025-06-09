"""Tests for CLI legal command."""

import shutil
import tempfile
import unittest

from typer.testing import CliRunner

from netvelocimeter.cli import app

runner = CliRunner()


class TestLegalCommand(unittest.TestCase):
    """Test cases for the CLI legal command."""

    def setUp(self):
        """Set up a clean test directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.temp_dir)

    def test_cli_legal_list(self):
        """Test the CLI app with a simple command."""
        result = runner.invoke(app, ["--provider=static", "legal", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("category: eula", result.stdout)
        self.assertIn("category: privacy", result.stdout)
        self.assertIn("category: service", result.stdout)

    def test_cli_legal_list_category_eula(self):
        """Test listing legal terms by eula category."""
        result = runner.invoke(app, ["--provider=static", "legal", "list", "--category", "eula"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("category: eula", result.stdout.lower())
        self.assertNotIn("category: privacy", result.stdout.lower())
        self.assertNotIn("category: service", result.stdout.lower())

    def test_cli_legal_list_category_privacy(self):
        """Test listing legal terms by privacy category."""
        result = runner.invoke(app, ["--provider=static", "legal", "list", "--category", "privacy"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("category: privacy", result.stdout.lower())
        self.assertNotIn("category: eula", result.stdout.lower())
        self.assertNotIn("category: service", result.stdout.lower())

    def test_cli_legal_list_category_service(self):
        """Test listing legal terms by service category."""
        result = runner.invoke(app, ["--provider=static", "legal", "list", "--category", "service"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("category: service", result.stdout.lower())
        self.assertNotIn("category: eula", result.stdout.lower())
        self.assertNotIn("category: privacy", result.stdout.lower())

    def test_cli_legal_status_all(self):
        """Test the CLI app with legal status command."""
        result = runner.invoke(
            app, ["--provider=static", "--config-root", self.temp_dir, "legal", "status"]
        )
        # Expecting 1 because no terms are accepted in temp config dir
        self.assertEqual(result.exit_code, 1)
        # Check that accepted false appears 3 times in stdout
        self.assertEqual(result.stdout.count("accepted:"), 3)
        self.assertEqual(result.stdout.count("False"), 3)
        self.assertIn("category: eula", result.stdout.lower())
        self.assertIn("category: privacy", result.stdout.lower())
        self.assertIn("category: service", result.stdout.lower())

    def test_cli_legal_status_category_eula(self):
        """Test the CLI app with legal status command for eula category."""
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "--config-root",
                self.temp_dir,
                "legal",
                "status",
                "--category",
                "eula",
            ],
        )
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.stdout.lower().count("accepted:"), 1)
        self.assertEqual(result.stdout.lower().count("false"), 1)
        self.assertNotIn("true", result.stdout.lower())
        self.assertIn("category: eula", result.stdout.lower())
        self.assertNotIn("category: privacy", result.stdout.lower())
        self.assertNotIn("category: service", result.stdout.lower())

    def test_cli_legal_accept_invalid_json(self):
        """Test the CLI app with legal accept command with invalid JSON input."""
        result = runner.invoke(
            app,
            ["--provider=static", "--config-root", self.temp_dir, "legal", "accept"],
            input="{notjson",
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("error accepting legal terms", result.stderr.lower())

    def test_cli_legal_accept_empty(self):
        """Test the CLI app with legal accept command with empty input."""
        result = runner.invoke(
            app, ["--provider=static", "--config-root", self.temp_dir, "legal", "accept"], input=""
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("no legal terms provided", result.stderr.lower())

    def test_cli_legal_accept_valid_eula(self):
        """Test the CLI app with legal accept command with valid JSON input for eula."""
        # check if terms are accepted
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "--config-root",
                self.temp_dir,
                "legal",
                "status",
                "--category",
                "eula",
            ],
        )
        self.assertEqual(result.exit_code, 1)
        self.assertRegex(result.stdout.lower(), r"accepted:\s+false")
        self.assertNotRegex(result.stdout.lower(), r"accepted:\s+true")

        # accept eula
        json_input = (
            '[{"text": "Test EULA", "url": "https://example.com/eula", "category": "eula"}]'
        )
        result = runner.invoke(
            app,
            ["--provider=static", "--config-root", self.temp_dir, "legal", "accept"],
            input=json_input,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result.stdout)
        self.assertFalse(result.stderr)

        # check if eula terms are accepted
        result = runner.invoke(
            app,
            [
                "--provider=static",
                "--config-root",
                self.temp_dir,
                "legal",
                "status",
                "--category",
                "eula",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stdout.lower(), r"accepted:\s+true")

        # check of all terms are accepted
        result = runner.invoke(
            app, ["--provider=static", "--config-root", self.temp_dir, "legal", "status"]
        )
        self.assertEqual(result.exit_code, 1)
        self.assertRegex(result.stdout.lower(), r"accepted:\s+true")
        self.assertRegex(result.stdout.lower(), r"accepted:\s+false")

    def test_cli_legal_accept_valid_all(self):
        """Test the CLI app with legal accept command with valid JSON input for all categories."""
        # check if terms are accepted
        result = runner.invoke(
            app, ["--provider=static", "--config-root", self.temp_dir, "legal", "status"]
        )
        self.assertEqual(result.exit_code, 1)
        self.assertRegex(result.stdout.lower(), r"accepted:\s+false")
        self.assertNotRegex(result.stdout.lower(), r"accepted:\s+true")

        # accept all terms
        json_input = (
            '[{"text": "Test EULA", "url": "https://example.com/eula", "category": "eula"}, '
            '{"text": "Test Privacy", "url": "https://example.com/privacy", "category": "privacy"}, '
            '{"text": "Test Terms", "url": "https://example.com/terms", "category": "service"}]'
        )
        result = runner.invoke(
            app,
            ["--provider=static", "--config-root", self.temp_dir, "legal", "accept"],
            input=json_input,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result.stdout)
        self.assertFalse(result.stderr)

        # check if all terms are accepted
        result = runner.invoke(
            app, ["--provider=static", "--config-root", self.temp_dir, "legal", "status"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stdout.lower(), r"accepted:\s+true")
        self.assertNotRegex(result.stdout.lower(), r"accepted:\s+false")

    def test_cli_legal_list_help(self):
        """Test the CLI app with legal list command help."""
        result = runner.invoke(app, ["legal", "list", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stdout, r"List legal terms(.|\n)+--category")

    def test_cli_legal_status_help(self):
        """Test the CLI app with legal status command help."""
        result = runner.invoke(app, ["legal", "status", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stdout, r"Status for(.|\n)+--category")

    def test_cli_legal_accept_help(self):
        """Test the CLI app with legal accept command help."""
        result = runner.invoke(app, ["legal", "accept", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stdout, r"Accept legal terms(.|\n)+--help")
