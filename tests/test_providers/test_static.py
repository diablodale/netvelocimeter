"""Tests for the StaticProvider."""

from datetime import timedelta
import shutil
import tempfile
import unittest

from packaging.version import Version

from netvelocimeter import get_provider
from netvelocimeter.providers.base import ServerInfo
from netvelocimeter.providers.static import StaticProvider
from netvelocimeter.terms import LegalTermsCategory


class TestStaticProvider(unittest.TestCase):
    """Test the StaticProvider implementation."""

    def setUp(self):
        """Set up a clean test directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.temp_dir)

    def test_get_provider(self):
        """Test getting the provider."""
        provider_class = get_provider("static")
        self.assertIsNotNone(provider_class)

    def test_default_initialization(self):
        """Test default initialization of StaticProvider."""
        provider = StaticProvider(config_root=self.temp_dir)

        # Check default version
        self.assertEqual(str(provider._version), "1.2.3+c0ffee")

        # Check default legal terms
        all_terms = provider._legal_terms()
        self.assertEqual(len(all_terms), 3)  # EULA, Service, Privacy

        eula_terms = provider._legal_terms(category=LegalTermsCategory.EULA)
        self.assertEqual(len(eula_terms), 1)
        self.assertEqual(eula_terms[0].text, "Test EULA")
        self.assertEqual(eula_terms[0].url, "https://example.com/eula")

        service_terms = provider._legal_terms(category=LegalTermsCategory.SERVICE)
        self.assertEqual(len(service_terms), 1)
        self.assertEqual(service_terms[0].text, "Test Terms")
        self.assertEqual(service_terms[0].url, "https://example.com/terms")

        privacy_terms = provider._legal_terms(category=LegalTermsCategory.PRIVACY)
        self.assertEqual(len(privacy_terms), 1)
        self.assertEqual(privacy_terms[0].text, "Test Privacy")
        self.assertEqual(privacy_terms[0].url, "https://example.com/privacy")

    def test_attribute_separation(self):
        """Test attribute separation in StaticProvider."""
        provider1 = StaticProvider(version="1.0.0", config_root=self.temp_dir)
        provider2 = StaticProvider(version="2.0.0", config_root=self.temp_dir)
        self.assertNotEqual(provider1._version, provider2._version)

    def test_custom_initialization(self):
        """Test custom initialization of StaticProvider."""
        provider = StaticProvider(
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
            config_root=self.temp_dir,
        )

        # Check custom version
        self.assertEqual(provider._version, Version("2.0.0+test"))

        # Check custom legal terms
        all_terms = provider._legal_terms()
        self.assertEqual(len(all_terms), 2)  # EULA and Privacy, but no Service

        # Verify EULA terms
        eula_terms = provider._legal_terms(category=LegalTermsCategory.EULA)
        self.assertEqual(len(eula_terms), 1)
        self.assertEqual(eula_terms[0].text, "Custom EULA")
        self.assertEqual(eula_terms[0].url, "https://example.com/custom-eula")

        # Verify Service terms (should be empty)
        service_terms = provider._legal_terms(category=LegalTermsCategory.SERVICE)
        self.assertEqual(len(service_terms), 0)

        # Verify Privacy terms
        privacy_terms = provider._legal_terms(category=LegalTermsCategory.PRIVACY)
        self.assertEqual(len(privacy_terms), 1)
        self.assertEqual(privacy_terms[0].text, "Custom Privacy")
        self.assertEqual(privacy_terms[0].url, "https://example.com/custom-privacy")

    def test_get_servers(self):
        """Test getting server list."""
        provider = StaticProvider(config_root=self.temp_dir)
        servers = provider._servers

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
            download_speed=150.0,
            upload_speed=30.0,
            ping_latency=timedelta(milliseconds=20.0),
            ping_jitter=timedelta(milliseconds=4.0),
            packet_loss=1.2,
            config_root=self.temp_dir,
        )

        # Accept all legal terms first
        provider._accept_terms(provider._legal_terms())

        result = provider._measure()

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
        provider = StaticProvider(config_root=self.temp_dir)

        # Accept all legal terms first
        provider._accept_terms(provider._legal_terms())

        # Test with valid server ID
        result = provider._measure(server_id=3)
        self.assertEqual(result.server_info.id, 3)
        self.assertEqual(result.server_info.name, "Test Server 3")

        # Test with invalid server ID (should raise ValueError)
        with self.assertRaises(ValueError):
            provider._measure(server_id=10)  # Out of range

        with self.assertRaises(ValueError):
            provider._measure(server_id="invalid")  # Wrong type

    def test_measure_with_server_host(self):
        """Test measurement with specific server host."""
        provider = StaticProvider(config_root=self.temp_dir)

        # Accept all legal terms first
        provider._accept_terms(provider._legal_terms())

        # Test with valid server host
        result = provider._measure(server_host="test4.example.com")
        self.assertEqual(result.server_info.host, "test4.example.com")
        self.assertEqual(result.server_info.id, 4)

        # Test with invalid server host (should raise ValueError)
        with self.assertRaises(ValueError):
            provider._measure(server_host="invalid.example.com")


class TestStaticProviderLegalTerms(unittest.TestCase):
    """Test the StaticProvider implementation legal terms."""

    def setUp(self):
        """Set up a clean test directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.temp_dir)

    def test_static_provider_legal_terms(self):
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
        eula_terms = [term for term in terms if term.category == LegalTermsCategory.EULA]
        self.assertEqual(len(eula_terms), 1)
        self.assertEqual(eula_terms[0].text, "Test EULA")
        self.assertEqual(eula_terms[0].url, "https://example.com/eula")

        # Test with category api
        eula_terms = provider._legal_terms(category=LegalTermsCategory.EULA)
        self.assertTrue(all(term.category == LegalTermsCategory.EULA for term in eula_terms))
        self.assertEqual(len(eula_terms), 1)
        self.assertEqual(eula_terms[0].text, "Test EULA")
        self.assertEqual(eula_terms[0].url, "https://example.com/eula")
        self.assertEqual(eula_terms[0].category, LegalTermsCategory.EULA)

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

    def test_static_provider_acceptance(self):
        """Test terms acceptance tracking."""
        provider = StaticProvider(config_root=self.temp_dir)

        # Initially no terms are accepted
        self.assertFalse(provider._has_accepted_terms())

        # Accept all terms
        terms = provider._legal_terms()
        provider._accept_terms(terms)

        # Now all terms should be accepted
        self.assertTrue(provider._has_accepted_terms())

    def test_static_provider_acceptance_twins(self):
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

    def test_static_provider_acceptance_all_then_single(self):
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
        eula_terms = provider2._legal_terms(category=LegalTermsCategory.EULA)
        provider2._accept_terms(eula_terms)

        # Should have accepted all terms
        self.assertTrue(provider2._has_accepted_terms())

        # Including acceptance of EULA
        self.assertTrue(provider2._has_accepted_terms(eula_terms))

    def test_static_provider_acceptance_progressive(self):
        """Test terms acceptance tracking."""
        provider = StaticProvider(config_root=self.temp_dir)

        # Initially no terms are accepted
        self.assertFalse(provider._has_accepted_terms())

        # Accept EULA terms
        eula_terms = provider._legal_terms(category=LegalTermsCategory.EULA)
        provider._accept_terms(eula_terms)

        # Only EULA terms should be accepted
        self.assertTrue(provider._has_accepted_terms(eula_terms))
        self.assertFalse(provider._has_accepted_terms())

        # Accept Service terms
        service_terms = provider._legal_terms(category=LegalTermsCategory.SERVICE)
        provider._accept_terms(service_terms)

        # Now EULA and Service terms should be accepted
        self.assertTrue(provider._has_accepted_terms(eula_terms))
        self.assertTrue(provider._has_accepted_terms(service_terms))
        self.assertFalse(provider._has_accepted_terms())

        # Accept Privacy terms
        privacy_terms = provider._legal_terms(category=LegalTermsCategory.PRIVACY)
        provider._accept_terms(privacy_terms)

        # Now EULA, Service, and Privacy terms should be accepted
        self.assertTrue(provider._has_accepted_terms(eula_terms))
        self.assertTrue(provider._has_accepted_terms(service_terms))
        self.assertTrue(provider._has_accepted_terms(privacy_terms))

        # Now all terms should be accepted
        self.assertTrue(provider._has_accepted_terms())

    def test_static_provider_acceptance_no_terms(self):
        """Test terms acceptance tracking with no terms."""
        provider = StaticProvider(
            eula_text=None,
            eula_url=None,
            terms_text=None,
            terms_url=None,
            privacy_text=None,
            privacy_url=None,
            config_root=self.temp_dir,
        )

        # Should return empty list of terms
        terms = provider._legal_terms()
        self.assertEqual(len(terms), 0)

        # With no terms, should be considered accepted
        self.assertTrue(provider._has_accepted_terms())
