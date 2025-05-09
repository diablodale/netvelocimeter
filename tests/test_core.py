"""Tests for the core functionality."""

import shutil
import tempfile
from unittest import TestCase, mock

from packaging.version import Version

from netvelocimeter import (
    NetVelocimeter,
    get_provider,
    library_version,
    list_providers,
    register_provider,
)
from netvelocimeter.core import _PROVIDERS
from netvelocimeter.exceptions import LegalAcceptanceError
from netvelocimeter.providers.base import BaseProvider, MeasurementResult, ServerIDType
from netvelocimeter.terms import LegalTerms, LegalTermsCategory


class MockProviderWithTerms(BaseProvider):
    """Mock provider with legal terms."""

    @property
    def _version(self) -> Version:
        """Return a mock version."""
        return Version("2.1.3+g123456")

    def _measure(
        self, server_id: ServerIDType | None = None, server_host: str | None = None
    ) -> MeasurementResult:
        """Mock measurement method."""
        return MeasurementResult(download_speed=1.0, upload_speed=1.0)

    def _legal_terms(self, category=LegalTermsCategory.ALL):
        """Return mock legal terms."""
        corpus = [
            LegalTerms(text="EULA", category=LegalTermsCategory.EULA),
            LegalTerms(text="TERMS", category=LegalTermsCategory.SERVICE),
            LegalTerms(text="PRIVACY", category=LegalTermsCategory.PRIVACY),
        ]
        if category == LegalTermsCategory.ALL:
            return corpus
        return [term for term in corpus if term.category == category]


class TestNetVelocimeter(TestCase):
    """Tests for NetVelocimeter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

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
        # Get the list of providers
        providers = list_providers()

        # Check it's a list of provider info objects
        self.assertIsInstance(providers, list)
        self.assertTrue(
            all(
                hasattr(provider, "name") and hasattr(provider, "description")
                for provider in providers
            )
        )

        # Check expected providers exist
        provider_names = [provider.name for provider in providers]
        self.assertIn("ookla", provider_names)
        self.assertIn("static", provider_names)

        # Check descriptions are lists of non-empty strings
        for provider in providers:
            self.assertIsInstance(provider.description, list)

            # Each line should be a non-empty string
            self.assertTrue(
                all(
                    isinstance(line, str) and line.strip() == line and line
                    for line in provider.description
                )
            )

        # Test each provider's docstring is properly processed
        # Get the raw providers
        provider_classes = {name: get_provider(name) for name in provider_names}

        # Check each provider's description matches its processed docstring
        for provider in providers:
            provider_class = provider_classes[provider.name]
            expected_description = [
                stripped_line
                for line in provider_class.__doc__.splitlines()
                if (stripped_line := line.strip())
            ]
            self.assertEqual(provider.description, expected_description)

    def test_initialize_with_unknown_parameter(self):
        """Test initializing with an unknown parameter logs a debug message."""
        with self.assertLogs(logger="netvelocimeter.core", level="DEBUG") as log:
            _ = NetVelocimeter(unknown_param="test")

            # Verify log content
            self.assertEqual(len(log.records), 1)
            self.assertEqual(log.records[0].levelname, "WARNING")
            self.assertIn("does not support parameters", log.output[0])
            self.assertIn("unknown_param", log.output[0])

    def test_provider_version_access(self):
        """Test accessing provider version."""
        # Mock the get_provider function instead of the OoklaProvider directly
        with mock.patch("netvelocimeter.core.get_provider") as mock_get_provider:
            # Create a mock provider class and instance
            mock_instance = mock.MagicMock()
            mock_instance._version = Version("1.2.3")
            mock_provider_class = mock.MagicMock(return_value=mock_instance)

            # Set up get_provider to return our mock provider class
            mock_get_provider.return_value = mock_provider_class

            nv = NetVelocimeter()
            self.assertEqual(nv.version, Version("1.2.3"))

    def test_netvelocimeter_legal_terms(self):
        """Test NetVelocimeter legal_terms method."""
        with mock.patch("netvelocimeter.core.get_provider") as mock_get_provider:
            # Create a mock provider class
            mock_get_provider.return_value = MockProviderWithTerms

            # Create NetVelocimeter instance
            nv = NetVelocimeter()

            # Test getting all terms
            terms = nv.legal_terms()
            self.assertEqual(len(terms), 3)

            # Test getting specific category
            eula_terms = nv.legal_terms(category=LegalTermsCategory.EULA)
            self.assertEqual(len(eula_terms), 1)
            self.assertEqual(eula_terms[0].text, "EULA")

    def test_netvelocimeter_name(self):
        """Test NetVelocimeter name property."""
        # register a mock provider
        register_provider("test_netvelocimeter_name", MockProviderWithTerms)

        # Create NetVelocimeter instance
        nv = NetVelocimeter(provider="test_netvelocimeter_name")

        # Test name property
        self.assertEqual(nv.name, "test_netvelocimeter_name")

    def test_netvelocimeter_description(self):
        """Test NetVelocimeter description property."""
        # register a mock provider
        register_provider("test_netvelocimeter_description", MockProviderWithTerms)

        # Create NetVelocimeter instance
        nv = NetVelocimeter(provider="test_netvelocimeter_description")

        # Test description property
        self.assertIsInstance(nv.description, list)
        self.assertTrue(all(isinstance(line, str) and line.strip() for line in nv.description))
        self.assertEqual(nv.description[0], "Mock provider with legal terms.")

    def test_netvelocimeter_library_version_as_version_object(self):
        """Test NetVelocimeter library version as Version object."""
        # Test library version property
        from netvelocimeter import __version__

        self.assertEqual(library_version(), Version(__version__))

    def test_netvelocimeter_servers(self):
        """Test NetVelocimeter servers property."""
        # register a mock provider
        register_provider("test_netvelocimeter_servers", MockProviderWithTerms)

        # Create NetVelocimeter instance
        nv = NetVelocimeter(provider="test_netvelocimeter_servers", config_root=self.temp_dir)

        # Test servers property
        with self.assertRaises(LegalAcceptanceError):
            _ = nv.servers

        # Accept legal terms
        nv.accept_terms(nv.legal_terms())

        # Test servers property again
        with self.assertRaises(NotImplementedError):
            _ = nv.servers

    def test_netvelocimeter_measure(self):
        """Test NetVelocimeter measure method."""
        # register a mock provider
        register_provider("test_netvelocimeter_measure", MockProviderWithTerms)

        # Create NetVelocimeter instance
        nv = NetVelocimeter(provider="test_netvelocimeter_measure", config_root=self.temp_dir)

        # Test measure method without accepting terms
        with self.assertRaises(LegalAcceptanceError):
            nv.measure()

        # Accept legal terms
        nv.accept_terms(nv.legal_terms())

        # Test measure method with invalid parameters
        with self.assertRaises(ValueError):
            _ = nv.measure(server_id="12345", server_host="test.server.com")

        # Test measure method with no parameters
        result = nv.measure()
        self.assertIsInstance(result, MeasurementResult)
        self.assertEqual(result.download_speed, 1.0)
        self.assertEqual(result.upload_speed, 1.0)

        # Test measure method with specific server
        result = nv.measure(server_id=1)
        self.assertIsInstance(result, MeasurementResult)
        self.assertEqual(result.download_speed, 1.0)
        self.assertEqual(result.upload_speed, 1.0)

        # Test measure method with specific server host
        result = nv.measure(server_host="test.server.com")
        self.assertIsInstance(result, MeasurementResult)
        self.assertEqual(result.download_speed, 1.0)
        self.assertEqual(result.upload_speed, 1.0)


class TestProviderRegistration(TestCase):
    """Test the provider-related functions."""

    def test_register_custom_provider(self):
        """Test registering a custom provider."""

        # Create a test provider class
        class TestProvider(BaseProvider):
            """Test provider for unit tests."""

            @property
            def _version(self) -> Version:
                """Return a mock version."""
                return Version("1.0.0")

            def _legal_terms(self, category=LegalTermsCategory.ALL):
                """Return mock legal terms."""
                return []

            def _measure(self, server_id=None, server_host=None):
                return MeasurementResult(download_speed=1.0, upload_speed=1.0)

        # Register it
        register_provider("test_register_custom_provider", TestProvider)

        # Should be available via get_provider
        provider_class = get_provider("test_register_custom_provider")
        self.assertEqual(provider_class, TestProvider)

        # Should appear in list_providers
        providers = list_providers()
        provider_names = [provider.name for provider in providers]
        self.assertIn("test_register_custom_provider", provider_names)

        # Find this provider's info
        provider_info = next(p for p in providers if p.name == "test_register_custom_provider")

        # Check description is a list of non-empty strings
        self.assertIsInstance(provider_info.description, list)
        self.assertTrue(
            all(isinstance(line, str) and line.strip() for line in provider_info.description)
        )

        # Check first line matches first non-empty line of docstring
        self.assertEqual(len(provider_info.description), 1)
        self.assertEqual(provider_info.description[0], "Test provider for unit tests.")

    def test_register_custom_provider_multiline_doc(self):
        """Test registering a custom provider."""

        # Create an actual test provider class instead of a mock instance
        class TestMockProvider(BaseProvider):
            """Test provider for unit tests.

            The first line of this __doc__ is an empty line.
            This test ensures registration works with multiline docstrings.
            """

            @property
            def _version(self) -> Version:
                """Return a mock version."""
                return Version("1.0.0")

            def _legal_terms(self, category=LegalTermsCategory.ALL):
                """Return mock legal terms."""
                return []

            def _measure(self, server_id=None, server_host=None):
                return MeasurementResult(download_speed=1.0, upload_speed=1.0)

        # Register it
        register_provider("test_register_custom_provider_multiline_doc", TestMockProvider)

        # Should be available via get_provider
        provider_class = get_provider("test_register_custom_provider_multiline_doc")
        self.assertEqual(provider_class, TestMockProvider)

        # Should appear in list_providers
        providers = list_providers()
        provider_names = [provider.name for provider in providers]
        self.assertIn("test_register_custom_provider_multiline_doc", provider_names)

        # Find this provider's info
        provider_info = next(
            p for p in providers if p.name == "test_register_custom_provider_multiline_doc"
        )

        # Check description is a list of non-empty strings
        self.assertIsInstance(provider_info.description, list)
        self.assertTrue(
            all(isinstance(line, str) and line.strip() for line in provider_info.description)
        )

        # Check first line matches first non-empty line of docstring
        self.assertEqual(provider_info.description[0], "Test provider for unit tests.")

        # Check that all expected lines are included
        expected_lines = [
            "Test provider for unit tests.",
            "The first line of this __doc__ is an empty line.",
            "This test ensures registration works with multiline docstrings.",
        ]
        self.assertEqual(provider_info.description, expected_lines)


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
            """Non-provider test class."""

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
            """Test provider for duplicates."""

            @property
            def _version(self) -> Version:
                """Return a mock version."""
                return Version("1.0.0")

            def _legal_terms(self, category=LegalTermsCategory.ALL):
                """Return mock legal terms."""
                return []

            def _measure(self, server_id=None, server_host=None):
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
            """Test provider with invalid name."""

            @property
            def _version(self) -> Version:
                """Return a mock version."""
                return Version("1.0.0")

            def _legal_terms(self, category=LegalTermsCategory.ALL):
                """Return mock legal terms."""
                return []

            def _measure(self, server_id=None, server_host=None):
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
            @property
            def _version(self) -> Version:
                """Mock version."""
                return Version("1.0.0")

            def _legal_terms(self, category=LegalTermsCategory.ALL):
                """Mock legal terms."""
                return []

            def _measure(self, server_id=None, server_host=None):
                """Mock measurement."""
                pass

        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            register_provider("test_no_doc", TestProviderNoDoc)

        self.assertIn("must have a docstring", str(context.exception))
