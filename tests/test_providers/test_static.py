"""
Tests for the StaticProvider.
"""

from datetime import timedelta
import shutil
import tempfile
import unittest

from packaging.version import Version

from netvelocimeter import get_provider
from netvelocimeter.providers.base import ServerInfo
from netvelocimeter.providers.static import StaticProvider


class TestStaticProvider(unittest.TestCase):
    """Test the StaticProvider implementation."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_get_provider(self):
        """Test getting the provider."""
        provider_class = get_provider("static")
        self.assertIsNotNone(provider_class)

    def test_default_initialization(self):
        """Test default initialization of StaticProvider."""
        provider = StaticProvider(self.temp_dir)

        # Check default version
        self.assertEqual(str(provider.version), "1.2.3+c0ffee")

        # Check default legal requirements
        legal = provider.legal_requirements
        self.assertTrue(legal.requires_acceptance)
        self.assertEqual(legal.eula_text, "Test EULA")
        self.assertEqual(legal.eula_url, "https://example.com/eula")
        self.assertEqual(legal.terms_text, "Test Terms")
        self.assertEqual(legal.terms_url, "https://example.com/terms")
        self.assertEqual(legal.privacy_text, "Test Privacy")
        self.assertEqual(legal.privacy_url, "https://example.com/privacy")

    def test_custom_initialization(self):
        """Test custom initialization of StaticProvider."""
        provider = StaticProvider(
            binary_dir=self.temp_dir,
            requires_acceptance=False,
            eula_text="Custom EULA",
            eula_url="https://example.com/custom-eula",
            terms_text=None,  # Test with None value
            terms_url=None,
            privacy_text="Custom Privacy",
            privacy_url="https://example.com/custom-privacy",
            download_speed=200.0,
            upload_speed=40.0,
            download_latency=timedelta(milliseconds=50.0),
            upload_latency=timedelta(milliseconds=70.0),
            ping_latency=timedelta(milliseconds=15.0),
            ping_jitter=timedelta(milliseconds=5.0),
            packet_loss=2.5,
            version="2.0.0+test",
            accepted_eula=True,
            accepted_terms=True,
            accepted_privacy=True
        )

        # Check custom version
        self.assertEqual(provider.version, Version("2.0.0+test"))

        # Check custom legal requirements
        legal = provider.legal_requirements
        self.assertFalse(legal.requires_acceptance)
        self.assertEqual(legal.eula_text, "Custom EULA")
        self.assertEqual(legal.eula_url, "https://example.com/custom-eula")
        self.assertIsNone(legal.terms_text)
        self.assertIsNone(legal.terms_url)
        self.assertEqual(legal.privacy_text, "Custom Privacy")
        self.assertEqual(legal.privacy_url, "https://example.com/custom-privacy")

        # Test acceptance flags
        self.assertTrue(provider._accepted_eula)
        self.assertTrue(provider._accepted_terms)
        self.assertTrue(provider._accepted_privacy)

    def test_get_servers(self):
        """Test getting server list."""
        provider = StaticProvider(self.temp_dir)
        servers = provider.get_servers()

        # Should have 5 test servers
        self.assertEqual(len(servers), 5)
        for server in servers:
            self.assertIsInstance(server, ServerInfo)
            self.assertIsInstance(server.name, str)
            self.assertIsInstance(server.id, int)

        # Check first and last servers
        self.assertEqual(servers[0].id, 1)
        self.assertEqual(servers[0].name, "Test Server 1")
        self.assertEqual(servers[0].host, "test1.example.com")

        self.assertEqual(servers[4].id, 5)
        self.assertEqual(servers[4].name, "Test Server 5")
        self.assertEqual(servers[4].host, "test5.example.com")

    def test_measure_without_server(self):
        """Test measurement without server specification."""
        provider = StaticProvider(
            binary_dir=self.temp_dir,
            download_speed=150.0,
            upload_speed=30.0,
            ping_latency=timedelta(milliseconds=20.0),
            ping_jitter=timedelta(milliseconds=4.0),
            packet_loss=1.2
        )

        result = provider.measure()

        # Check measurement results
        self.assertEqual(result.download_speed, 150.0)
        self.assertEqual(result.upload_speed, 30.0)
        self.assertEqual(result.ping_latency, timedelta(milliseconds=20.0))
        self.assertEqual(result.ping_jitter, timedelta(milliseconds=4.0))
        self.assertEqual(result.packet_loss, 1.2)

        # Check default server info (should use server 1)
        self.assertEqual(result.server_info.name, "Test Server 1")
        self.assertEqual(result.server_info.id, 1)

        # Check the persist_url field
        self.assertEqual(result.persist_url, "https://example.com/results/static-test-1234")

        # Check the id field format
        self.assertIsNotNone(result.id)
        self.assertTrue(result.id.startswith("static-test-1-"))

    def test_measure_with_server_id(self):
        """Test measurement with specific server ID."""
        provider = StaticProvider(self.temp_dir)

        # Test with valid server ID
        result = provider.measure(server_id=3)
        self.assertEqual(result.server_info.id, 3)
        self.assertEqual(result.server_info.name, "Test Server 3")

        # Test with invalid server ID (should raise ValueError)
        with self.assertRaises(ValueError):
            provider.measure(server_id=10)  # Out of range

        with self.assertRaises(ValueError):
            provider.measure(server_id="invalid")  # Wrong type

    def test_measure_with_server_host(self):
        """Test measurement with specific server host."""
        provider = StaticProvider(self.temp_dir)

        # Test with valid server host
        result = provider.measure(server_host="test4.example.com")
        self.assertEqual(result.server_info.host, "test4.example.com")
        self.assertEqual(result.server_info.id, 4)

        # Test with invalid server host (should raise ValueError)
        with self.assertRaises(ValueError):
            provider.measure(server_host="invalid.example.com")

    def test_legal_acceptance(self):
        """Test legal acceptance checks."""
        # Provider that requires acceptance
        provider = StaticProvider(
            binary_dir=self.temp_dir,
            requires_acceptance=True
        )

        # Without acceptance should fail
        self.assertFalse(provider.check_acceptance())

        # With partial acceptance should fail
        self.assertFalse(provider.check_acceptance(accepted_eula=True))
        self.assertFalse(provider.check_acceptance(accepted_terms=True, accepted_privacy=True))

        # With full acceptance should pass
        self.assertTrue(provider.check_acceptance(
            accepted_eula=True,
            accepted_terms=True,
            accepted_privacy=True
        ))

        # Provider that doesn't require acceptance
        provider_no_req = StaticProvider(
            binary_dir=self.temp_dir,
            requires_acceptance=False
        )

        # Should pass even without acceptance
        self.assertTrue(provider_no_req.check_acceptance())
