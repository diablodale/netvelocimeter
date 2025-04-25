"""Tests for the base provider."""

from datetime import timedelta
from unittest import TestCase

from packaging.version import Version

from netvelocimeter.providers.base import BaseProvider, MeasurementResult, ServerInfo
from netvelocimeter.providers.static import StaticProvider
from netvelocimeter.terms import LegalTermsCategory


class MockProvider(BaseProvider):
    """A concrete implementation of BaseProvider for testing."""

    def measure(self, server_id=None, server_host=None):
        """Implement the abstract method."""
        # Return a minimal measurement result
        return MeasurementResult(
            download_speed=100.0,
            upload_speed=50.0,
            ping_latency=timedelta(milliseconds=20),
            ping_jitter=timedelta(milliseconds=5),
        )

    @property
    def version(self) -> Version:
        """Return a mock version."""
        return Version("2.1.3+g123456")


class TestBaseProviderImplementation(TestCase):
    """Test the BaseProvider implementation."""

    def test_base_provider_get_servers(self):
        """Test default get_servers implementation raises NotImplementedError."""
        provider = MockProvider()
        with self.assertRaises(NotImplementedError):
            _ = provider.servers

    def test_base_provider_version(self):
        """Test BaseProvider version handling."""
        provider = MockProvider()
        self.assertEqual(str(provider.version), "2.1.3+g123456")
        self.assertEqual(provider.version, Version("2.1.3+g123456"))

    def test_base_provider_legal_terms(self):
        """Test the legal_terms method."""
        # Create a provider with terms
        provider = StaticProvider()
        terms = provider.legal_terms()

        # Verify it's a collection
        self.assertIsInstance(terms, list)

        # Verify it has the default categories
        categories = {term.category for term in terms}
        self.assertIn(LegalTermsCategory.EULA, categories)
        self.assertIn(LegalTermsCategory.SERVICE, categories)
        self.assertIn(LegalTermsCategory.PRIVACY, categories)

        # Test with specified category
        eula_terms = provider.legal_terms(category=LegalTermsCategory.EULA)
        self.assertTrue(all(term.category == LegalTermsCategory.EULA for term in eula_terms))

        # Provider with no terms
        provider_no_terms = StaticProvider(
            eula_text=None,
            eula_url=None,
            terms_text=None,
            terms_url=None,
            privacy_text=None,
            privacy_url=None,
        )

        no_terms = provider_no_terms.legal_terms()
        self.assertEqual(len(no_terms), 0)

    def test_base_provider_acceptance(self):
        """Test terms acceptance tracking."""
        provider = StaticProvider()

        # Initially no terms are accepted
        self.assertFalse(provider.has_accepted_terms())

        # Accept all terms
        terms = provider.legal_terms()
        provider.accept_terms(terms)

        # Now all terms should be accepted
        self.assertTrue(provider.has_accepted_terms())

        # Test accepting a specific category
        provider2 = StaticProvider()
        eula_terms = provider2.legal_terms(category=LegalTermsCategory.EULA)
        provider2.accept_terms(eula_terms)

        # Should have accepted EULA but not all terms
        self.assertTrue(provider2.has_accepted_terms(eula_terms))
        self.assertFalse(provider2.has_accepted_terms())

        # Provider with no terms
        provider_no_terms = StaticProvider(
            eula_text=None,
            eula_url=None,
            terms_text=None,
            terms_url=None,
            privacy_text=None,
            privacy_url=None,
        )

        # With no terms, should be considered accepted
        self.assertTrue(provider_no_terms.has_accepted_terms())


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
            id="test-measurement-123456",
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
            server_info=ServerInfo(name="Test Server", id=1234, host="test.example.com"),
        )
        str_result = str(result)
        # Check that output contains expected values
        self.assertIn("Server: Test Server (1234)", str_result)
        self.assertIn("Download: 100.50 Mbps", str_result)
        self.assertIn("Upload: 20.25 Mbps", str_result)

    def test_server_info_with_optional_id(self):
        """Test ServerInfo with and without ID."""
        # Server with ID
        server_with_id = ServerInfo(name="Test Server", id="1234", host="test.example.com")
        self.assertEqual(server_with_id.id, "1234")
        self.assertEqual(server_with_id.name, "Test Server")

        # Server without ID
        server_without_id = ServerInfo(name="Test Server 2", host="test2.example.com")
        self.assertIsNone(server_without_id.id)
        self.assertEqual(server_without_id.name, "Test Server 2")

    def test_server_info_with_no_name(self):
        """Test ServerInfo with no name."""
        with self.assertRaises(ValueError):
            _ = ServerInfo(name=None, id="1234", host="test.example.com")
        with self.assertRaises(TypeError):
            _ = ServerInfo(id="1234", host="test.example.com")

    def test_measurement_result_str_with_server_without_id(self):
        """Test string representation of measurement results with server without ID."""
        server_info = ServerInfo(name="Test Server No ID", host="test.example.com")
        result = MeasurementResult(
            download_speed=100.5,
            upload_speed=20.25,
            ping_latency=timedelta(milliseconds=15.75),
            server_info=server_info,
        )

        str_result = str(result)
        self.assertIn("Server: Test Server No ID", str_result)
        self.assertNotIn("(", str_result)  # Should not contain parentheses for ID

    def test_measurement_result_with_no_speeds(self):
        """Test MeasurementResult with no speeds."""
        with self.assertRaises(TypeError):
            _ = MeasurementResult(download_speed=123, ping_latency=timedelta(milliseconds=15.75))
        with self.assertRaises(TypeError):
            _ = MeasurementResult(upload_speed=123, ping_latency=timedelta(milliseconds=15.75))
        with self.assertRaises(ValueError):
            _ = MeasurementResult(
                download_speed=None, upload_speed=None, ping_latency=timedelta(milliseconds=15.75)
            )
