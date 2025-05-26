"""Tests for the base provider."""

import shutil
import tempfile
from unittest import TestCase

from packaging.version import Version

from netvelocimeter.legal import LegalTermsCategory
from netvelocimeter.providers.base import BaseProvider, MeasurementResult, ServerInfo
from netvelocimeter.providers.static import StaticProvider
from netvelocimeter.utils.rates import DataRateMbps, Percentage, TimeDuration


class MockProvider(BaseProvider):
    """A concrete implementation of BaseProvider for testing."""

    @property
    def _version(self) -> Version:
        """Mock version."""
        return Version("2.1.3+g123456")

    def _legal_terms(self, categories=LegalTermsCategory.ALL):
        """Mock legal terms."""
        return []

    def _measure(self, server_id=None, server_host=None):
        """Mock measurement method."""
        # Return a minimal measurement result
        return MeasurementResult(
            download_speed=100.0,
            upload_speed=50.0,
            ping_latency=TimeDuration(milliseconds=20),
            ping_jitter=TimeDuration(milliseconds=5),
        )


class TestBaseProviderImplementation(TestCase):
    """Test the BaseProvider implementation."""

    def setUp(self):
        """Set up a clean test directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.temp_dir)

    def test_base_provider_get_servers(self):
        """Test default get_servers implementation raises NotImplementedError."""
        provider = MockProvider()
        with self.assertRaises(NotImplementedError):
            _ = provider._servers

    def test_base_provider_version(self):
        """Test BaseProvider version handling."""
        provider = MockProvider()
        self.assertEqual(str(provider._version), "2.1.3+g123456")
        self.assertEqual(provider._version, Version("2.1.3+g123456"))

    def test_base_provider_legal_terms(self):
        """Test the legal_terms method."""
        # Create a provider with terms
        provider = StaticProvider(config_root=self.temp_dir)
        terms = provider._legal_terms()

        # Verify it's a collection
        self.assertIsInstance(terms, list)

        # Verify it has the default categories
        categories = {term.category for term in terms}
        self.assertIn(LegalTermsCategory.EULA, categories)
        self.assertIn(LegalTermsCategory.SERVICE, categories)
        self.assertIn(LegalTermsCategory.PRIVACY, categories)

        # Test with specified category
        eula_terms = provider._legal_terms(categories=LegalTermsCategory.EULA)
        self.assertTrue(all(term.category == LegalTermsCategory.EULA for term in eula_terms))

        # Provider with no terms
        provider_no_terms = StaticProvider(
            eula_text=None,
            eula_url=None,
            terms_text=None,
            terms_url=None,
            privacy_text=None,
            privacy_url=None,
            config_root=self.temp_dir,
        )

        no_terms = provider_no_terms._legal_terms()
        self.assertEqual(len(no_terms), 0)

    def test_base_provider_acceptance(self):
        """Test terms acceptance tracking."""
        provider = StaticProvider(config_root=self.temp_dir)

        # Initially no terms are accepted
        self.assertFalse(provider._has_accepted_terms())

        # Accept all terms
        terms = provider._legal_terms()
        provider._accept_terms(terms)

        # Now all terms should be accepted
        self.assertTrue(provider._has_accepted_terms())

    def test_base_provider_acceptance_twins(self):
        """Test terms acceptance tracking."""
        provider = StaticProvider(config_root=self.temp_dir)

        # Initially no terms are accepted
        self.assertFalse(provider._has_accepted_terms())

        # Accept all terms
        terms = provider._legal_terms()
        provider._accept_terms(terms)

        # Now all terms should be accepted
        self.assertTrue(provider._has_accepted_terms())

        # Create a second provider with the same config root
        provider2 = StaticProvider(config_root=self.temp_dir)

        # Should also have accepted terms
        self.assertTrue(provider2._has_accepted_terms())

    def test_base_provider_acceptance_all_then_single(self):
        """Test terms acceptance tracking."""
        provider = StaticProvider(config_root=self.temp_dir)

        # Initially no terms are accepted
        self.assertFalse(provider._has_accepted_terms())

        # Accept all terms
        terms = provider._legal_terms()
        provider._accept_terms(terms)

        # Now all terms should be accepted
        self.assertTrue(provider._has_accepted_terms())

        # Create a second provider with the same config root
        provider2 = StaticProvider(config_root=self.temp_dir)

        # Accepting a specific category (which is already accepted above)
        eula_terms = provider2._legal_terms(categories=LegalTermsCategory.EULA)
        provider2._accept_terms(eula_terms)

        # Should have accepted all terms
        self.assertTrue(provider2._has_accepted_terms())

        # Including acceptance of EULA
        self.assertTrue(provider2._has_accepted_terms(eula_terms))

    def test_base_provider_acceptance_no_terms(self):
        """Test terms acceptance tracking with no terms."""
        provider_no_terms = StaticProvider(
            eula_text=None,
            eula_url=None,
            terms_text=None,
            terms_url=None,
            privacy_text=None,
            privacy_url=None,
            config_root=self.temp_dir,
        )

        # With no terms, should be considered accepted
        self.assertTrue(provider_no_terms._has_accepted_terms())


class TestMeasurementResult(TestCase):
    """Tests for MeasurementResult class."""

    def test_format_representation(self):
        """Test format representation of measurement results."""
        result = MeasurementResult(
            download_speed=DataRateMbps(100.5),
            upload_speed=DataRateMbps(20.25),
            download_latency=TimeDuration(milliseconds=10.5),
            upload_latency=TimeDuration(milliseconds=5.25),
            ping_latency=TimeDuration(milliseconds=15.75),
            ping_jitter=TimeDuration(milliseconds=3.5),
            packet_loss=Percentage(0.1),
            persist_url="https://example.com/results/1234",
            id="test-measurement-123456",
        )

        str_result = format(result)
        # Check that output contains expected values
        self.assertRegex(str_result, r"download_speed:\s+100.50 Mbps")
        self.assertRegex(str_result, r"upload_speed:\s+20.25 Mbps")
        self.assertRegex(str_result, r"download_latency:\s+10.50 ms")
        self.assertRegex(str_result, r"upload_latency:\s+5.25 ms")
        self.assertRegex(str_result, r"ping_latency:\s+15.75 ms")
        self.assertRegex(str_result, r"ping_jitter:\s+3.50 ms")
        self.assertRegex(str_result, r"packet_loss:\s+0.10 %")
        self.assertRegex(str_result, r"id:\s+test-measurement-123456")
        self.assertRegex(str_result, r"url:\s+https://example.com/results/1234")

    def test_format_representation_with_server_info(self):
        """Test format representation of measurement results with server info."""
        result = MeasurementResult(
            download_speed=DataRateMbps(100.5),
            upload_speed=DataRateMbps(20.25),
            ping_latency=TimeDuration(milliseconds=15.75),
            server_info=ServerInfo(name="Test Server", id=1234, host="test.example.com"),
        )
        str_result = format(result)
        # Check that output contains expected values
        self.assertRegex(str_result, r"server_name:\s+Test Server")
        self.assertRegex(str_result, r"server_id:\s+1234")
        self.assertRegex(str_result, r"download_speed:\s+100.50 Mbps")
        self.assertRegex(str_result, r"upload_speed:\s+20.25 Mbps")

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

    def test_measurement_result_format_with_server_without_id(self):
        """Test format representation of measurement results with server without ID."""
        server_info = ServerInfo(name="Test Server No ID", host="test.example.com")
        result = MeasurementResult(
            download_speed=DataRateMbps(100.5),
            upload_speed=DataRateMbps(20.25),
            ping_latency=TimeDuration(milliseconds=15.75),
            server_info=server_info,
        )

        str_result = format(result)
        self.assertRegex(str_result, r"server_name:\s+Test Server No ID")
        self.assertNotIn("id:", str_result)

    def test_measurement_result_with_no_speeds(self):
        """Test MeasurementResult with no speeds."""
        with self.assertRaises(TypeError):
            _ = MeasurementResult(download_speed=123, ping_latency=TimeDuration(milliseconds=15.75))
        with self.assertRaises(TypeError):
            _ = MeasurementResult(upload_speed=123, ping_latency=TimeDuration(milliseconds=15.75))
        with self.assertRaises(ValueError):
            _ = MeasurementResult(
                download_speed=None,
                upload_speed=None,
                ping_latency=TimeDuration(milliseconds=15.75),
            )
