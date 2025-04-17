import os
import unittest
from unittest import mock
import tempfile
from datetime import timedelta

from netvelocimeter import NetVelocimeter
from netvelocimeter.exceptions import LegalAcceptanceError
from netvelocimeter.providers.base import ProviderLegalRequirements, BaseProvider, MeasurementResult


class MockProvider(BaseProvider):
    """Mock provider requiring legal acceptance for testing."""

    def __init__(self, binary_dir: str):
        super().__init__(binary_dir)
        self._accepted_eula = False
        self._accepted_terms = False
        self._accepted_privacy = False
        self.version = "1.0.0-test"

    @property
    def legal_requirements(self) -> ProviderLegalRequirements:
        return ProviderLegalRequirements(
            eula_text="Test EULA",
            eula_url="https://example.com/eula",
            terms_text="Test Terms",
            terms_url="https://example.com/terms",
            privacy_text="Test Privacy",
            privacy_url="https://example.com/privacy",
            requires_acceptance=True
        )

    def measure(self, **kwargs) -> MeasurementResult:
        return MeasurementResult(
            download_speed=100.0,
            upload_speed=50.0,
            ping_latency=timedelta(milliseconds=10.0),
            ping_jitter=timedelta(milliseconds=2.0)
        )


class TestLegalRequirements(unittest.TestCase):
    """Test legal requirements functionality."""

    @mock.patch('netvelocimeter.core.get_provider')
    def setUp(self, mock_get_provider):
        """Set up test environment."""
        mock_get_provider.return_value = MockProvider
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @mock.patch('netvelocimeter.core.get_provider')
    def test_default_no_acceptance(self, mock_get_provider):
        """Test that measurements fail without legal acceptance."""
        mock_get_provider.return_value = MockProvider

        nv = NetVelocimeter(binary_dir=self.temp_dir)

        with self.assertRaises(LegalAcceptanceError):
            nv.measure()

    @mock.patch('netvelocimeter.core.get_provider')
    def test_partial_acceptance_fails(self, mock_get_provider):
        """Test that partial acceptance fails."""
        mock_get_provider.return_value = MockProvider

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
        mock_get_provider.return_value = MockProvider

        nv = NetVelocimeter(
            binary_dir=self.temp_dir,
            accept_eula=True,
            accept_terms=True,
            accept_privacy=True
        )

        result = nv.measure()
        self.assertEqual(result.download_speed, 100.0)
        self.assertEqual(result.upload_speed, 50.0)
        self.assertEqual(result.ping_latency, timedelta(milliseconds=10.0))

    @mock.patch('netvelocimeter.core.get_provider')
    def test_get_legal_requirements(self, mock_get_provider):
        """Test fetching legal requirements."""
        mock_get_provider.return_value = MockProvider

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
        mock_get_provider.return_value = MockProvider

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
