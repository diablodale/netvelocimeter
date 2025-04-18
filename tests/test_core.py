"""
Tests for the core functionality.
"""

import tempfile
from unittest import mock, TestCase
from packaging.version import Version

from netvelocimeter.core import register_provider, _PROVIDERS
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

    def test_get_provider_with_nonexistent_name(self):
        """Test getting an invalid provider."""
        with self.assertRaises(ValueError):
            get_provider("nonexistent")

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

class TestProviderRegistration(TestCase):
    """Test the provider-related functions."""

    def test_register_custom_provider(self):
        """Test registering a custom provider."""
        # Create a test provider class
        class TestProvider(BaseProvider):
            """Test provider for unit tests"""
            def measure(self, server_id=None, server_host=None):
                return MeasurementResult(download_speed=1.0, upload_speed=1.0)

        # Register it
        register_provider("test_register_custom_provider", TestProvider)

        # Should be available via get_provider
        provider_class = get_provider("test_register_custom_provider")
        self.assertEqual(provider_class, TestProvider)

        # Should appear in list_providers
        providers = list_providers()
        self.assertIn("test_register_custom_provider", providers)

        # Should have description in info listing
        providers_with_info = list_providers(include_info=True)
        provider_info = {name: desc for name, desc in providers_with_info}
        self.assertIn("test_register_custom_provider", provider_info)
        self.assertEqual(provider_info["test_register_custom_provider"], "Test provider for unit tests")

    def test_register_custom_provider_multiline_doc(self):
        """Test registering a custom provider."""
        # Create an actual test provider class instead of a mock instance
        class TestMockProvider(BaseProvider):
            """
            Test provider for unit tests.

            The first line of this __doc__ is an empty line.
            This test ensures registration works with multiline docstrings.
            """
            def measure(self, server_id=None, server_host=None):
                return MeasurementResult(download_speed=1.0, upload_speed=1.0)

        # Register it
        register_provider("test_register_custom_provider_multiline_doc", TestMockProvider)

        # Should be available via get_provider
        provider_class = get_provider("test_register_custom_provider_multiline_doc")
        self.assertEqual(provider_class, TestMockProvider)

        # Should appear in list_providers
        providers = list_providers()
        self.assertIn("test_register_custom_provider_multiline_doc", providers)

        # Should have description in info listing
        providers_with_info = list_providers(include_info=True)
        provider_info = {name: desc for name, desc in providers_with_info}
        self.assertIn("test_register_custom_provider_multiline_doc", provider_info)
        self.assertEqual(provider_info["test_register_custom_provider_multiline_doc"], "Test provider for unit tests.")

class TestProviderRegistrationErrors(TestCase):
    """Test error scenarios for provider registration."""

    def setUp(self):
        """Set up test environment."""
        # Save original providers to restore after test
        self._original_providers = _PROVIDERS.copy()

    def tearDown(self):
        """Clean up test environment."""
        # Restore original providers
        _PROVIDERS.clear()
        _PROVIDERS.update(self._original_providers)

    def test_register_non_provider_class(self):
        """Test registering a class that doesn't inherit from BaseProvider."""
        # Create a class that doesn't inherit from BaseProvider
        class NonProviderClass:
            """Non-provider test class"""
            pass

        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            register_provider("test_non_provider", NonProviderClass)

        self.assertIn("Must be a concrete subclass of BaseProvider", str(context.exception))

    def test_register_abstract_base_provider(self):
        """Test registering the BaseProvider abstract class directly."""
        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            register_provider("base_provider", BaseProvider)

        # This should fail due to abstract method 'measure' not being implemented
        self.assertIn("Must be a concrete subclass of BaseProvider", str(context.exception))

    def test_register_duplicate_provider(self):
        """Test registering a provider with a name already in use."""
        # Create a valid provider class
        class TestProvider(BaseProvider):
            """Test provider for duplicates"""
            def measure(self, server_id=None, server_host=None):
                pass

        # Register first time - should succeed
        register_provider("test_register_duplicate_provider", TestProvider)

        # Register again with same name - should fail
        with self.assertRaises(ValueError) as context:
            register_provider("test_register_duplicate_provider", TestProvider)

        self.assertIn("already registered", str(context.exception))

        # Test case insensitivity
        with self.assertRaises(ValueError) as context:
            register_provider("TEST_REGISTER_DUPLICATE_PROVIDER", TestProvider)

        self.assertIn("already registered", str(context.exception))

    def test_register_invalid_name(self):
        """Test registering a provider with an invalid name."""
        # Create a valid provider class
        class TestProvider(BaseProvider):
            """Test provider with invalid name"""
            def measure(self, server_id=None, server_host=None):
                pass

        # Test with invalid identifier (contains spaces)
        with self.assertRaises(ValueError) as context:
            register_provider("invalid name", TestProvider)

        self.assertIn("Must be a valid Python identifier", str(context.exception))

        # Test with invalid identifier (starts with number)
        with self.assertRaises(ValueError) as context:
            register_provider("123invalid", TestProvider)

        self.assertIn("Must be a valid Python identifier", str(context.exception))

        # Test with invalid identifier (contains special chars)
        with self.assertRaises(ValueError) as context:
            register_provider("invalid@name", TestProvider)

        self.assertIn("Must be a valid Python identifier", str(context.exception))

    def test_register_without_docstring(self):
        """Test registering a provider class without a docstring."""
        # Create a provider class without a docstring
        class TestProviderNoDoc(BaseProvider):
            def measure(self, server_id=None, server_host=None):
                pass

        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            register_provider("test_no_doc", TestProviderNoDoc)

        self.assertIn("must have a docstring", str(context.exception))

    @mock.patch('netvelocimeter.core._discover_providers')
    def test_auto_discovery_on_first_registration(self, mock_discover):
        """Test that _discover_providers is called on first registration."""
        # Clear existing providers
        _PROVIDERS.clear()

        # Create a valid provider
        class TestAutoDiscoverProvider(BaseProvider):
            """Test provider for auto-discovery"""
            def measure(self, server_id=None, server_host=None):
                pass

        # Register a provider - should trigger discovery
        register_provider("test_auto_discovery_on_first_registration_1", TestAutoDiscoverProvider)

        # Verify discovery was called
        mock_discover.assert_called_once()

        # Register another provider - should not trigger discovery again
        class TestSecondProvider(BaseProvider):
            """Second test provider"""
            def measure(self, server_id=None, server_host=None):
                pass

        register_provider("test_auto_discovery_on_first_registration_2", TestSecondProvider)

        # Verify discovery was not called again
        self.assertEqual(mock_discover.call_count, 1)
