"""
Tests for the core functionality.
"""

import tempfile
from unittest import mock, TestCase
from packaging.version import Version

from netvelocimeter.core import register_provider
from netvelocimeter import NetVelocimeter, get_provider
from netvelocimeter.providers.base import MeasurementResult, BaseProvider

class TestNetVelocimeter(TestCase):
    """Tests for NetVelocimeter class."""

    def test_get_provider(self):
        """Test getting a provider."""
        provider_class = get_provider("ookla")
        self.assertIsNotNone(provider_class)

        # Test alias
        provider_class_alias = get_provider("speedtest")
        self.assertEqual(provider_class, provider_class_alias)

        # Test case insensitivity
        provider_class_case = get_provider("OoKlA")
        self.assertEqual(provider_class, provider_class_case)

    def test_invalid_provider(self):
        """Test getting an invalid provider."""
        with self.assertRaises(ValueError):
            get_provider("nonexistent")

    def test_register_custom_provider(self):
        """Test registering a custom provider."""
        # Create a mock provider class
        mock_provider = mock.MagicMock(spec=BaseProvider)

        # Register it with a new name
        register_provider("custom_test", mock_provider)

        # Verify it can be retrieved
        retrieved = get_provider("custom_test")
        assert retrieved == mock_provider

    def test_initialize_with_binary_dir(self):
        """Test initializing with a binary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch('netvelocimeter.providers.ookla.OoklaProvider._ensure_binary') as mock_ensure:
                with mock.patch('netvelocimeter.providers.ookla.OoklaProvider._get_version') as mock_get_version:
                    mock_ensure.return_value = "/fake/path"
                    mock_get_version.return_value = "1.0.0-test"

                    nv = NetVelocimeter(binary_dir=temp_dir)
                    self.assertEqual(nv.provider.binary_dir, temp_dir)

    def test_provider_version_access(self):
        """Test accessing provider version."""
        # Mock the get_provider function instead of the OoklaProvider directly
        with mock.patch('netvelocimeter.core.get_provider') as mock_get_provider:
            # Create a mock provider class and instance
            mock_instance = mock.MagicMock()
            mock_instance.version = Version("1.2.3")
            mock_provider_class = mock.MagicMock(return_value=mock_instance)

            # Set up get_provider to return our mock provider class
            mock_get_provider.return_value = mock_provider_class

            nv = NetVelocimeter()
            self.assertEqual(nv.get_provider_version(), Version("1.2.3"))
