"""Test legal requirements functionality."""

from datetime import timedelta
import shutil
import tempfile
import unittest
from unittest import mock

from netvelocimeter import NetVelocimeter
from netvelocimeter.exceptions import LegalAcceptanceError
from netvelocimeter.providers.static import StaticProvider
from netvelocimeter.terms import LegalTermsCategory


class TestLegalRequirements(unittest.TestCase):
    """Test legal requirements functionality."""

    def setUp(self):
        """Set up a clean test directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.temp_dir)

    @mock.patch("netvelocimeter.core.get_provider")
    def test_default_no_acceptance(self, mock_get_provider):
        """Test that measurements fail without legal acceptance."""
        mock_get_provider.return_value = StaticProvider

        # Create NetVelocimeter without accepting terms
        nv = NetVelocimeter(config_root=self.temp_dir)

        # Verify that measurement fails without accepting terms
        with self.assertRaises(LegalAcceptanceError):
            nv.measure()

    @mock.patch("netvelocimeter.core.get_provider")
    def test_partial_acceptance_fails(self, mock_get_provider):
        """Test that partial acceptance fails."""
        mock_get_provider.return_value = StaticProvider

        # Create NetVelocimeter
        nv = NetVelocimeter(config_root=self.temp_dir)

        # Only accept EULA terms
        eula_terms = nv.legal_terms(categories=LegalTermsCategory.EULA)
        nv.accept_terms(eula_terms)

        # Should still fail because not all terms are accepted
        with self.assertRaises(LegalAcceptanceError):
            nv.measure()

        # Create fresh instance and accept EULA and Service terms but not Privacy
        nv2 = NetVelocimeter(config_root=self.temp_dir)
        nv2.accept_terms(nv2.legal_terms(categories=LegalTermsCategory.EULA))
        nv2.accept_terms(nv2.legal_terms(categories=LegalTermsCategory.SERVICE))

        # Should still fail because privacy terms aren't accepted
        with self.assertRaises(LegalAcceptanceError):
            nv2.measure()

    @mock.patch("netvelocimeter.core.get_provider")
    def test_full_acceptance_succeeds(self, mock_get_provider):
        """Test that full acceptance allows measurements."""
        mock_get_provider.return_value = StaticProvider

        # Create NetVelocimeter
        nv = NetVelocimeter(config_root=self.temp_dir)

        # Accept all terms
        nv.accept_terms(nv.legal_terms())

        # Measurement should succeed
        result = nv.measure()
        self.assertEqual(result.download_speed, 100.0)
        self.assertEqual(result.upload_speed, 50.0)
        self.assertEqual(result.ping_latency, timedelta(milliseconds=25.0))

    @mock.patch("netvelocimeter.core.get_provider")
    def test_legal_terms_retrieval(self, mock_get_provider):
        """Test retrieving legal terms."""
        mock_get_provider.return_value = StaticProvider

        nv = NetVelocimeter(config_root=self.temp_dir)
        terms = nv.legal_terms()

        # Check that we have terms
        self.assertTrue(terms)
        self.assertTrue(len(terms) == 3)

        # Get categories
        categories = {term.category for term in terms}
        self.assertIn(LegalTermsCategory.EULA, categories)
        self.assertIn(LegalTermsCategory.SERVICE, categories)
        self.assertIn(LegalTermsCategory.PRIVACY, categories)

        # Test filtering by category
        eula_terms = nv.legal_terms(categories=LegalTermsCategory.EULA)
        self.assertTrue(all(term.category == LegalTermsCategory.EULA for term in eula_terms))

        # Test filtering by ALL
        all_terms = nv.legal_terms(categories=LegalTermsCategory.ALL)
        self.assertTrue(len(all_terms) == 3)
        self.assertTrue(all(term.category in categories for term in all_terms))

        # Test filtering by ALL in a collection alone
        all_terms = nv.legal_terms(categories=[LegalTermsCategory.ALL])
        self.assertTrue(len(all_terms) == 3)
        self.assertTrue(all(term.category in categories for term in all_terms))

        # Test filtering by ALL in a collection
        all_terms = nv.legal_terms(categories=[LegalTermsCategory.PRIVACY, LegalTermsCategory.ALL])
        self.assertTrue(len(all_terms) == 3)
        self.assertTrue(all(term.category in categories for term in all_terms))

        # Test term content
        for term in eula_terms:
            if term.category == LegalTermsCategory.EULA:
                self.assertEqual(term.url, "https://example.com/eula")
                self.assertEqual(term.text, "Test EULA")

    @mock.patch("netvelocimeter.core.get_provider")
    def test_has_accepted_terms(self, mock_get_provider):
        """Test checking acceptance status."""
        mock_get_provider.return_value = StaticProvider

        # No acceptance
        nv = NetVelocimeter(config_root=self.temp_dir)
        self.assertFalse(nv.has_accepted_terms())

        # Partial acceptance
        nv = NetVelocimeter(config_root=self.temp_dir)
        nv.accept_terms(nv.legal_terms(categories=LegalTermsCategory.EULA))
        self.assertFalse(nv.has_accepted_terms())  # Should be false for all terms
        self.assertTrue(
            nv.has_accepted_terms(nv.legal_terms(categories=LegalTermsCategory.EULA))
        )  # But true for just EULA

        # Full acceptance
        nv = NetVelocimeter(config_root=self.temp_dir)
        nv.accept_terms(nv.legal_terms())
        self.assertTrue(nv.has_accepted_terms())

    def test_provider_without_terms(self):
        """Test provider with no legal terms."""
        provider = StaticProvider(
            eula_text=None,
            eula_url=None,
            terms_text=None,
            terms_url=None,
            privacy_text=None,
            privacy_url=None,
            config_root=self.temp_dir,
        )

        # When there are no terms, should return empty collection
        terms = provider._legal_terms()
        self.assertEqual(len(terms), 0)

        # Provider with no terms should be considered to have all terms accepted
        self.assertTrue(provider._has_accepted_terms())
