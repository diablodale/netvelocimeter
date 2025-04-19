"""
Tests for the base provider.
"""

from datetime import timedelta
import shutil
import tempfile
from unittest import TestCase

from netvelocimeter.providers.base import BaseProvider, MeasurementResult, ServerInfo
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

class TestMeasurementResult(TestCase):
    """Tests for MeasurementResult class."""

    def test_str_representation(self):
        """Test string representation of measurement results."""
        result = MeasurementResult(
            download_speed=100.5,
            upload_speed=20.25,
            ping_latency=timedelta(milliseconds=15.75),
            ping_jitter=timedelta(milliseconds=3.5),
            packet_loss=0.1,
            persist_url="https://example.com/results/1234",
            id="test-measurement-123456"
        )

        str_result = str(result)
        # Check that output contains expected values
        self.assertIn("Download: 100.50 Mbps", str_result)
        self.assertIn("Upload: 20.25 Mbps", str_result)
        self.assertIn("Ping Latency: 15.75 ms", str_result)
        self.assertIn("Ping Jitter: 3.50 ms", str_result)
        self.assertIn("Packet Loss: 0.10%", str_result)
        self.assertIn("ID: test-measurement-123456", str_result)
        self.assertIn("URL: https://example.com/results/1234", str_result)

    def test_str_representation_with_server_info(self):
        """Test string representation of measurement results with server info."""
        result = MeasurementResult(
            download_speed=100.5,
            upload_speed=20.25,
            ping_latency=timedelta(milliseconds=15.75),
            server_info=ServerInfo(
                name="Test Server",
                id=1234,
                host="test.example.com"
            )
        )
        str_result = str(result)
        # Check that output contains expected values
        self.assertIn("Server: Test Server (1234)", str_result)
        self.assertIn("Download: 100.50 Mbps", str_result)
        self.assertIn("Upload: 20.25 Mbps", str_result)

    def test_server_info_with_optional_id(self):
        """Test ServerInfo with and without ID."""
        # Server with ID
        server_with_id = ServerInfo(
            name="Test Server",
            id="1234",
            host="test.example.com"
        )
        self.assertEqual(server_with_id.id, "1234")
        self.assertEqual(server_with_id.name, "Test Server")

        # Server without ID
        server_without_id = ServerInfo(
            name="Test Server 2",
            host="test2.example.com"
        )
        self.assertIsNone(server_without_id.id)
        self.assertEqual(server_without_id.name, "Test Server 2")

    def test_server_info_with_no_name(self):
        """Test ServerInfo with no name."""
        with self.assertRaises(ValueError):
            server_info = ServerInfo(
                name=None,
                id="1234",
                host="test.example.com"
            )
        with self.assertRaises(TypeError):
            server_info = ServerInfo(
                id="1234",
                host="test.example.com"
            )

    def test_measurement_result_str_with_server_without_id(self):
        """Test string representation of measurement results with server without ID."""
        server_info = ServerInfo(
            name="Test Server No ID",
            host="test.example.com"
        )
        result = MeasurementResult(
            download_speed=100.5,
            upload_speed=20.25,
            ping_latency=timedelta(milliseconds=15.75),
            server_info=server_info
        )

        str_result = str(result)
        self.assertIn("Server: Test Server No ID", str_result)
        self.assertNotIn("(", str_result)  # Should not contain parentheses for ID

    def test_measurement_result_with_no_speeds(self):
        """Test MeasurementResult with no speeds."""
        with self.assertRaises(TypeError):
            result = MeasurementResult(
                download_speed=123,
                ping_latency=timedelta(milliseconds=15.75)
            )
        with self.assertRaises(TypeError):
            result = MeasurementResult(
                upload_speed=123,
                ping_latency=timedelta(milliseconds=15.75)
            )
        with self.assertRaises(ValueError):
            result = MeasurementResult(
                download_speed=None,
                upload_speed=None,
                ping_latency=timedelta(milliseconds=15.75)
            )
