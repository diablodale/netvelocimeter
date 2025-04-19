"""
Tests for the core functionality.
"""

import tempfile
from unittest import mock, TestCase
from packaging.version import Version

from netvelocimeter.core import register_provider
from netvelocimeter import NetVelocimeter, get_provider, list_providers
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
        # Create a test provider class
        class TestProvider(BaseProvider):
            """Test provider for unit tests"""
            def measure(self, server_id=None, server_host=None):
                return MeasurementResult(download_speed=1.0, upload_speed=1.0)

        # Register it with a new name
        register_provider("custom_test", TestProvider)

        # Verify it can be retrieved
        retrieved = get_provider("custom_test")
        self.assertEqual(retrieved, TestProvider)

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

class TestProviderFunctions(TestCase):
    """Test the provider-related functions."""

    def test_list_providers(self):
        """Test listing available providers."""
        # Should return at least the default provider
        providers = list_providers()
        self.assertIsInstance(providers, list)
        self.assertIn("ookla", providers)
        self.assertIn("static", providers)

        # Test with include_info=True
        providers_with_info = list_providers(include_info=True)
        self.assertIsInstance(providers_with_info, list)
        self.assertIsInstance(providers_with_info[0], tuple)
        self.assertEqual(len(providers_with_info[0]), 2)

        # Ensure at least one provider name matches between the two calls
        plain_names = set(providers)
        info_names = {name for name, _ in providers_with_info}
        self.assertTrue(plain_names.intersection(info_names))

    def test_register_custom_provider(self):
        """Test registering a custom provider."""
        # Create an actual test provider class instead of a mock instance
        class TestMockProvider(BaseProvider):
            """Test provider for unit tests"""
            def measure(self, server_id=None, server_host=None):
                return MeasurementResult(download_speed=1.0, upload_speed=1.0)

        # Register it
        register_provider("test_provider", TestMockProvider)

        # Should be available via get_provider
        provider_class = get_provider("test_provider")
        self.assertEqual(provider_class, TestMockProvider)

        # Should appear in list_providers
        providers = list_providers()
        self.assertIn("test_provider", providers)

        # Should have description in info listing
        providers_with_info = list_providers(include_info=True)
        provider_info = {name: desc for name, desc in providers_with_info}
        self.assertIn("test_provider", provider_info)
        self.assertEqual(provider_info["test_provider"], "Test provider for unit tests")
