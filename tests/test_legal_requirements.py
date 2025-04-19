from datetime import timedelta
import tempfile
import unittest
from unittest import mock

from netvelocimeter import NetVelocimeter
from netvelocimeter.exceptions import LegalAcceptanceError
from netvelocimeter.providers.static import StaticProvider


class TestLegalRequirements(unittest.TestCase):
    """Test legal requirements functionality."""

    @mock.patch('netvelocimeter.core.get_provider')
    def setUp(self, mock_get_provider):
        """Set up test environment."""
        mock_get_provider.return_value = StaticProvider
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @mock.patch('netvelocimeter.core.get_provider')
    def test_default_no_acceptance(self, mock_get_provider):
        """Test that measurements fail without legal acceptance."""
        mock_get_provider.return_value = StaticProvider

        nv = NetVelocimeter(binary_dir=self.temp_dir)

        with self.assertRaises(LegalAcceptanceError):
            nv.measure()

    @mock.patch('netvelocimeter.core.get_provider')
    def test_partial_acceptance_fails(self, mock_get_provider):
        """Test that partial acceptance fails."""
        mock_get_provider.return_value = StaticProvider

        # Only accept EULA
        nv = NetVelocimeter(
            binary_dir=self.temp_dir,
            accept_eula=True
        )

        with self.assertRaises(LegalAcceptanceError):
            nv.measure()

        # Only accept EULA and Terms
        nv = NetVelocimeter(
            binary_dir=self.temp_dir,
            accept_eula=True,
            accept_terms=True
        )

        with self.assertRaises(LegalAcceptanceError):
            nv.measure()

    @mock.patch('netvelocimeter.core.get_provider')
    def test_full_acceptance_succeeds(self, mock_get_provider):
        """Test that full acceptance allows measurements."""
        mock_get_provider.return_value = StaticProvider

        nv = NetVelocimeter(
            binary_dir=self.temp_dir,
            accept_eula=True,
            accept_terms=True,
            accept_privacy=True
        )

        result = nv.measure()
        self.assertEqual(result.download_speed, 100.0)
        self.assertEqual(result.upload_speed, 50.0)
        self.assertEqual(result.ping_latency, timedelta(milliseconds=25.0))

    @mock.patch('netvelocimeter.core.get_provider')
    def test_get_legal_requirements(self, mock_get_provider):
        """Test fetching legal requirements."""
        mock_get_provider.return_value = StaticProvider

        nv = NetVelocimeter(binary_dir=self.temp_dir)
        legal = nv.get_legal_requirements()

        self.assertEqual(legal.eula_text, "Test EULA")
        self.assertEqual(legal.eula_url, "https://example.com/eula")
        self.assertEqual(legal.terms_text, "Test Terms")
        self.assertEqual(legal.terms_url, "https://example.com/terms")
        self.assertEqual(legal.privacy_text, "Test Privacy")
        self.assertEqual(legal.privacy_url, "https://example.com/privacy")
        self.assertTrue(legal.requires_acceptance)

    @mock.patch('netvelocimeter.core.get_provider')
    def test_check_legal_requirements(self, mock_get_provider):
        """Test checking legal requirements."""
        mock_get_provider.return_value = StaticProvider

        # No acceptance
        nv = NetVelocimeter(binary_dir=self.temp_dir)
        self.assertFalse(nv.check_legal_requirements())

        # Partial acceptance
        nv = NetVelocimeter(binary_dir=self.temp_dir, accept_eula=True)
        self.assertFalse(nv.check_legal_requirements())

        # Full acceptance
        nv = NetVelocimeter(
            binary_dir=self.temp_dir,
            accept_eula=True,
            accept_terms=True,
            accept_privacy=True
        )
        self.assertTrue(nv.check_legal_requirements())
