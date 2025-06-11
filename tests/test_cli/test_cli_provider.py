"""Tests for CLI provider command."""

import json
import unittest
from unittest import mock

from typer.testing import CliRunner

from netvelocimeter.cli import app

runner = CliRunner()


class TestProviderCommand(unittest.TestCase):
    """Test cases for the CLI provider command."""

    def test_provider_list_success(self):
        """Test 'provider list' outputs available providers."""
        result = runner.invoke(app, ["provider", "list"])
        self.assertEqual(result.exit_code, 0)
        # Should contain at least one known provider, e.g. "static"
        self.assertRegex(
            result.stdout, r"name:\s*static\ndescription:\s*Configurable.+\n\s+All.+\n\s+Five"
        )

    def test_provider_list_format_json(self):
        """Test 'provider list' with JSON output format."""
        result = runner.invoke(app, ["--format", "json", "provider", "list"])
        self.assertEqual(result.exit_code, 0)
        output = result.stdout.strip()
        self.assertTrue(output.startswith("["))
        self.assertTrue(output.endswith("]"))
        result = json.loads(output)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # validate dict in list has a field "name" with value "static" and
        # field "description" with value starting with "Configurable"
        self.assertTrue(
            any(
                (
                    provider["name"] == "static"
                    and provider["description"][0].startswith("Configurable")
                )
                for provider in result
            )
        )

    def test_provider_list_format_csv(self):
        """Test 'provider list' with CSV output format."""
        result = runner.invoke(app, ["--format", "csv", "provider", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.stdout.startswith(r'"name","description"'))
        self.assertIn(r'"static","Configurable', result.stdout)

    def test_provider_list_format_tsv(self):
        """Test 'provider list' with TSV output format."""
        result = runner.invoke(app, ["--format", "tsv", "provider", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.stdout.startswith("name\tdescription"))
        self.assertIn('static\t"Configurable', result.stdout)

    def test_provider_list_help(self):
        """Test 'provider list --help' outputs usage."""
        result = runner.invoke(app, ["provider", "list", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertRegex(result.stdout, r"List all available providers(.|\n)+Show this message")

    @mock.patch("netvelocimeter.cli.commands.provider.list_providers")
    def test_no_providers(self, mock_list_providers):
        """Test 'provider list' when no providers are available."""
        # mock list_providers() to return an empty list
        mock_list_providers.return_value = []

        # Run the command
        result = runner.invoke(app, ["provider", "list"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertRegex(result.stderr, r"ERROR.+No matching providers found.")
