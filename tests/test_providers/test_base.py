"""
Tests for the base provider.
"""

import shutil
import tempfile
import unittest
from datetime import timedelta

from netvelocimeter.providers.base import BaseProvider, MeasurementResult

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

class TestBaseProviderImplementation(unittest.TestCase):
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
