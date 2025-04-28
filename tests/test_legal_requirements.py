"""Test legal requirements functionality."""

from datetime import timedelta
import unittest
from unittest import mock

from netvelocimeter import NetVelocimeter
from netvelocimeter.exceptions import LegalAcceptanceError
from netvelocimeter.providers.static import StaticProvider
from netvelocimeter.terms import LegalTermsCategory


class TestLegalRequirements(unittest.TestCase):
    """Test legal requirements functionality."""

    @mock.patch("netvelocimeter.core.get_provider")
    def test_default_no_acceptance(self, mock_get_provider):
        """Test that measurements fail without legal acceptance."""
        mock_get_provider.return_value = StaticProvider

        # Create NetVelocimeter without accepting terms
        nv = NetVelocimeter()

        # Verify that measurement fails without accepting terms
        with self.assertRaises(LegalAcceptanceError):
            nv.measure()

    @mock.patch("netvelocimeter.core.get_provider")
    def test_partial_acceptance_fails(self, mock_get_provider):
        """Test that partial acceptance fails."""
        mock_get_provider.return_value = StaticProvider

        # Create NetVelocimeter
        nv = NetVelocimeter()

        # Only accept EULA terms
        eula_terms = nv.legal_terms(category=LegalTermsCategory.EULA)
        nv.accept_terms(eula_terms)

        # Should still fail because not all terms are accepted
        with self.assertRaises(LegalAcceptanceError):
            nv.measure()

        # Create fresh instance and accept EULA and Service terms but not Privacy
        nv2 = NetVelocimeter()
        nv2.accept_terms(nv2.legal_terms(category=LegalTermsCategory.EULA))
        nv2.accept_terms(nv2.legal_terms(category=LegalTermsCategory.SERVICE))

        # Should still fail because privacy terms aren't accepted
        with self.assertRaises(LegalAcceptanceError):
            nv2.measure()

    @mock.patch("netvelocimeter.core.get_provider")
    def test_full_acceptance_succeeds(self, mock_get_provider):
        """Test that full acceptance allows measurements."""
        mock_get_provider.return_value = StaticProvider

        # Create NetVelocimeter
        nv = NetVelocimeter()

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

        nv = NetVelocimeter()
        terms = nv.legal_terms()

        # Check that we have terms
        self.assertTrue(terms)

        # Get categories
        categories = {term.category for term in terms}
        self.assertIn(LegalTermsCategory.EULA, categories)
        self.assertIn(LegalTermsCategory.SERVICE, categories)
        self.assertIn(LegalTermsCategory.PRIVACY, categories)

        # Test filtering by category
        eula_terms = nv.legal_terms(category=LegalTermsCategory.EULA)
        self.assertTrue(all(term.category == LegalTermsCategory.EULA for term in eula_terms))

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
        nv = NetVelocimeter()
        self.assertFalse(nv.has_accepted_terms())

        # Partial acceptance
        nv = NetVelocimeter()
        nv.accept_terms(nv.legal_terms(category=LegalTermsCategory.EULA))
        self.assertFalse(nv.has_accepted_terms())  # Should be false for all terms
        self.assertTrue(
            nv.has_accepted_terms(nv.legal_terms(category=LegalTermsCategory.EULA))
        )  # But true for just EULA

        # Full acceptance
        nv = NetVelocimeter()
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
        )

        # When there are no terms, should return empty collection
        terms = provider._legal_terms()
        self.assertEqual(len(terms), 0)

        # Provider with no terms should be considered to have all terms accepted
        self.assertTrue(provider._has_accepted_terms())
