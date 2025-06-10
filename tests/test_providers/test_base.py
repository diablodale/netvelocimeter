"""Tests for the base provider."""

import shutil
import tempfile
from unittest import TestCase

from packaging.version import Version

from netvelocimeter.legal import LegalTermsCategory
from netvelocimeter.providers.base import BaseProvider, MeasurementResult, ServerInfo
from netvelocimeter.providers.provider_info import ProviderInfo
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


class TestServerInfo(TestCase):
    """Tests for ServerInfo class."""

    def test_server_info_with_optional_id(self):
        """Test ServerInfo with and without ID."""
        # Server with str ID
        server_with_str_id = ServerInfo(name="Test Server", id="1234", host="test.example.com")
        self.assertEqual(server_with_str_id.id, "1234")
        self.assertEqual(server_with_str_id.name, "Test Server")

        # Server with int ID
        server_with_int_id = ServerInfo(name="Test Server 2", id=5678, host="test2.example.com")
        self.assertEqual(server_with_int_id.id, 5678)
        self.assertEqual(server_with_int_id.name, "Test Server 2")

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
        with self.assertRaises(ValueError):
            _ = ServerInfo(name="", id="1234", host="test.example.com")

    def test_server_info_with_invalid_id(self):
        """Test ServerInfo with invalid ID."""
        with self.assertRaises(TypeError):
            _ = ServerInfo(name="Test Server", id=3.4, host="test.example.com")
        with self.assertRaises(TypeError):
            _ = ServerInfo(name="Test Server", id=[1, 3], host="test.example.com")

    def test_server_info_to_dict(self):
        """Test converting ServerInfo to dictionary."""
        server_info = ServerInfo(name="Test Server", id=1234, host="test.example.com")
        expected_dict = {
            "name": "Test Server",
            "id": 1234,
            "host": "test.example.com",
            "location": None,
            "country": None,
            "raw": None,
        }
        self.assertEqual(server_info.to_dict(), expected_dict)

    def test_format_representation(self):
        """Test format representation of server info."""
        server_info = ServerInfo(name="Test Server", id=1234, host="test.example.com")
        str_server_info = format(server_info)
        self.assertRegex(str_server_info, r"name:\s+Test Server")
        self.assertRegex(str_server_info, r"id:\s+1234")
        self.assertRegex(str_server_info, r"host:\s+test.example.com")


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

    def test_measurement_result_with_id_or_persist_url(self):
        """Test MeasurementResult with id or persist_url."""
        # With id
        result_with_id = MeasurementResult(
            download_speed=DataRateMbps(100.5),
            upload_speed=DataRateMbps(20.25),
            id="test-id-1234",
        )
        self.assertEqual(result_with_id.id, "test-id-1234")
        self.assertIsNone(result_with_id.persist_url)

        # With persist_url
        result_with_url = MeasurementResult(
            download_speed=DataRateMbps(100.5),
            upload_speed=DataRateMbps(20.25),
            persist_url="https://example.com/results/1234",
        )
        self.assertIsNone(result_with_url.id)
        self.assertEqual(result_with_url.persist_url, "https://example.com/results/1234")

    def test_measurement_result_with_raw_data(self):
        """Test MeasurementResult with raw data."""
        raw_data = {
            "download_speed": 100.5,
            "upload_speed": 20.25,
            "ping_latency": 15.75,
            "server_info": {"name": "Test Server", "id": 1234, "host": "test.example.com"},
        }
        result = MeasurementResult(
            download_speed=DataRateMbps(raw_data["download_speed"]),
            upload_speed=DataRateMbps(raw_data["upload_speed"]),
            ping_latency=TimeDuration(milliseconds=raw_data["ping_latency"]),
            server_info=ServerInfo(
                name=raw_data["server_info"]["name"],
                id=raw_data["server_info"]["id"],
                host=raw_data["server_info"]["host"],
            ),
            raw=raw_data,
        )
        self.assertEqual(result.raw, raw_data)

    def test_measurement_result_with_no_speeds(self):
        """Test MeasurementResult with no speeds."""
        with self.assertRaises(TypeError):
            _ = MeasurementResult(download_speed=123)
        with self.assertRaises(TypeError):
            _ = MeasurementResult(upload_speed=123)
        with self.assertRaises(TypeError):
            _ = MeasurementResult(download_speed=123, upload_speed=DataRateMbps(100.5))
        with self.assertRaises(TypeError):
            _ = MeasurementResult(download_speed=DataRateMbps(100.5), upload_speed=123)
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=None,
                upload_speed=None,
                ping_latency=TimeDuration(milliseconds=15.75),
            )

    def test_measurement_result_with_invalid_latencies_losses(self):
        """Test MeasurementResult with invalid latencies."""
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                download_latency="invalid",
            )
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                upload_latency="invalid",
            )
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                ping_latency="invalid",
            )
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                ping_jitter="invalid",
            )
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                packet_loss="invalid",
            )

    def test_measurement_result_with_invalid_server_info(self):
        """Test MeasurementResult with invalid server info."""
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                server_info="invalid",
            )
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                server_info=1234,
            )

    def test_measurement_result_with_invalid_persist_url_id_raw(self):
        """Test MeasurementResult with invalid other fields."""
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                persist_url=1234,
            )
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                id=1234,
            )
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                raw="invalid",
            )
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                raw=1234,
            )
        with self.assertRaises(TypeError):
            _ = MeasurementResult(
                download_speed=DataRateMbps(100.5),
                upload_speed=DataRateMbps(20.25),
                raw=["invalid", "data"],
            )


class TestProviderInfo(TestCase):
    """Tests for ProviderInfo class."""

    def test_provider_info_creation(self):
        """Test creating a ProviderInfo instance."""
        info = ProviderInfo(name="Test Provider", description=["A test provider"])
        self.assertEqual(info.name, "Test Provider")
        self.assertEqual(info.description, ["A test provider"])

    def test_provider_info_empty_name(self):
        """Test creating ProviderInfo with empty name raises ValueError."""
        with self.assertRaises(ValueError):
            _ = ProviderInfo(name="", description=["No name provider"])
        with self.assertRaises(TypeError):
            _ = ProviderInfo(description=["No name provider"])

    def test_provider_info_empty_description(self):
        """Test creating ProviderInfo with empty description raises ValueError."""
        with self.assertRaises(ValueError):
            _ = ProviderInfo(name="No Description", description=[])
        with self.assertRaises(TypeError):
            _ = ProviderInfo(name="No Description")

    def test_provider_info_to_dict(self):
        """Test converting ProviderInfo to dictionary."""
        info = ProviderInfo(name="Test Provider", description=["A test provider"])
        expected_dict = {
            "name": "Test Provider",
            "description": ["A test provider"],
        }
        self.assertEqual(info.to_dict(), expected_dict)

    def test_provider_info_formatting(self):
        """Test formatting ProviderInfo."""
        info = ProviderInfo(name="Test Provider", description=["A test provider"])
        formatted_str = format(info)
        self.assertRegex(formatted_str, r"name:\s+Test Provider")
        self.assertRegex(formatted_str, r"description:\s+A test provider")
