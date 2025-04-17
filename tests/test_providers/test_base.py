"""
Tests for the base provider.
"""

import shutil
import tempfile
from unittest import TestCase, mock
from datetime import timedelta

from netvelocimeter.providers.base import BaseProvider, MeasurementResult, ProviderLegalRequirements
from netvelocimeter.providers.static import StaticProvider

class MockProvider(BaseProvider):
    """A concrete implementation of BaseProvider for testing."""

    def measure(self, server_id=None, server_host=None):
        """Implement the abstract method."""
        # Return a minimal measurement result
        return MeasurementResult(
            download_speed=100.0,
            upload_speed=50.0,
            ping_latency=timedelta(milliseconds=20),
            ping_jitter=timedelta(milliseconds=5)
        )

class TestBaseProviderImplementation(TestCase):
    """Test the BaseProvider implementation."""

    def setUp(self):
        """Set up a test directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.temp_dir)

    def test_base_provider_get_servers(self):
        """Test default get_servers implementation raises NotImplementedError."""
        provider = MockProvider(self.temp_dir)
        with self.assertRaises(NotImplementedError):
            provider.get_servers()

    def test_base_provider_version(self):
        """Test BaseProvider version handling."""
        provider = MockProvider(self.temp_dir)
        self.assertEqual(str(provider.version), "0")

    def test_base_provider_check_acceptance_edge_cases(self):
        """Test all edge cases for the check_acceptance method."""


        # Test all combinations of acceptance
        provider = StaticProvider(self.temp_dir)
        for accepted_eula in [True, False]:
            for accepted_terms in [True, False]:
                for accepted_privacy in [True, False]:
                    if accepted_eula and accepted_terms and accepted_privacy:
                        self.assertTrue(provider.check_acceptance(accepted_eula, accepted_terms, accepted_privacy))
                    else:
                        self.assertFalse(provider.check_acceptance(accepted_eula, accepted_terms, accepted_privacy))

        # Test when requires_acceptance is False
        provider = StaticProvider(self.temp_dir, requires_acceptance=False)
        for accepted_eula in [True, False]:
            for accepted_terms in [True, False]:
                for accepted_privacy in [True, False]:
                    self.assertTrue(provider.check_acceptance(accepted_eula, accepted_terms, accepted_privacy))
