"""Core functionality for the NetVelocimeter library."""

import inspect
from typing import Any, TypeVar, final

from packaging.version import Version

from .exceptions import LegalAcceptanceError
from .providers.base import BaseProvider, MeasurementResult, ProviderInfo, ServerIDType, ServerInfo
from .terms import (
    LegalTerms,
    LegalTermsCategory,
    LegalTermsCategoryCollection,
    LegalTermsCollection,
)
from .utils.logger import get_logger

# Map of provider names to provider classes
_PROVIDERS: dict[str, type[BaseProvider]] = {}

# Get logger for the core component
logger = get_logger("core")

B = TypeVar("B", bound=BaseProvider)


def _normalize_provider_name(name: str) -> str:
    """Normalize a provider name.

    This function is primarily for internal use and provider developers.

    Args:
        name: Name of the provider to normalize

    Returns:
        Normalized provider name

    Raises:
        ValueError: If the name is not a valid identifier
    """
    name = name.lower()
    if not name.isidentifier():
        raise ValueError(f"Invalid provider name '{name}'. Must be a valid Python identifier.")
    return name


def register_provider(name: str, provider_class: type[B]) -> None:
    """Register a provider class with the library.

    This function is primarily for internal use and provider developers.
    It allows them to register their custom provider classes with the library.

    Args:
        name: Name to register the provider under
        provider_class: Provider class to register
    """
    # validate provider_class
    if not issubclass(provider_class, BaseProvider) or inspect.isabstract(provider_class):
        raise ValueError(
            f"Invalid provider class: {provider_class}. Must be a concrete subclass of BaseProvider."
        )

    # normalize name, check for duplicates, check for docstring
    name = _normalize_provider_name(name)
    if name in _PROVIDERS:
        raise ValueError(f"Provider '{name}' is already registered.")
    if not provider_class.__doc__:
        raise ValueError(f"Provider class '{provider_class.__name__}' must have a docstring.")
    _PROVIDERS[name] = provider_class


def get_provider(name: str) -> type[BaseProvider]:
    """Get a provider class by name.

    This function is primarily for internal use and provider developers.
    It allows them to directly access provider classes
    for customization, extension, or testing purposes.

    Args:
        name: Name of the provider to retrieve

    Returns:
        The provider class (not an instance)

    Raises:
        ValueError: If the requested provider is not found

    Example:
        # Create a custom provider with specific parameters
        ProviderClass = get_provider("ookla")
        custom_provider = ProviderClass(custom_option=True)
    """
    # Normalize name and retrieve provider class
    name = _normalize_provider_name(name)
    try:
        return _PROVIDERS[name]
    except KeyError as e:
        raise ValueError(
            f"Provider '{name}' not found. Available providers: {', '.join(_PROVIDERS.keys())}"
        ) from e


def list_providers() -> list[ProviderInfo]:
    """Get a list of all available providers.

    Returns:
        A list of provider info objects having name and description

    Examples:
        >>> list_providers()
        [ProviderInfo(name='ookla', description='Ookla Speedtest provider'),
        ProviderInfo(name='static', description='Static provider for testing')]
    """
    return [
        ProviderInfo(
            name=name,
            description=[
                stripped_line
                for line in provider.__doc__.splitlines()  # type: ignore[union-attr]
                if (stripped_line := line.strip())
            ],
        )
        for name, provider in _PROVIDERS.items()
    ]


def library_version() -> Version:
    """Get the version of the NetVelocimeter library as a Version object.

    This method returns a Version object which provides version comparison capabilities.
    For just the version string, use netvelocimeter.__version__ directly.

    Returns:
        NetVelocimeter library version as a Version object.
    """
    # Dynamic version import
    from . import __version__

    return Version(__version__)


class NetVelocimeter:
    """Main class for the NetVelocimeter library."""

    def __init__(
        self,
        provider: str = "ookla",
        **kwargs: Any,
    ) -> None:
        """Initialize the NetVelocimeter.

        Args:
            provider: The name of the provider to use.
            kwargs: Additional arguments to pass to the provider.

        """
        # Check if the provider is registered
        provider_class = get_provider(provider)

        # Inspect the provider class for supported parameters
        provider_params = inspect.signature(provider_class.__init__).parameters

        # Partition kwargs into supported and unsupported
        # Filter kwargs to only include parameters in the provider's signature
        # Skip 'self' which will be in the signature but not a valid kwarg
        filtered_kwargs = {}
        unsupported = []
        for k, v in kwargs.items():
            if k in provider_params and k != "self":
                filtered_kwargs[k] = v
            else:
                unsupported.append(k)

        # log unsupported parameters
        if unsupported:
            logger.debug(
                f"Provider '{provider}' does not support parameters: {', '.join(unsupported)}"
            )

        # create the provider instance
        self.provider = provider_class(**filtered_kwargs)
        self.provider_name = _normalize_provider_name(provider)

    @final
    def legal_terms(
        self, categories: LegalTermsCategory | LegalTermsCategoryCollection = LegalTermsCategory.ALL
    ) -> LegalTermsCollection:
        """Get legal terms of the provider.

        Args:
            categories: Category of terms to retrieve. Defaults to ALL.

        Returns:
            Collection of legal terms that match the requested category
        """
        return self.provider._legal_terms(categories)

    @final
    def has_accepted_terms(
        self, terms_or_collection: LegalTerms | LegalTermsCollection | None = None
    ) -> bool:
        """Check if the user has accepted the specified terms of the provider.

        Args:
            terms_or_collection: Terms to check. If None, checks all legal terms for the current provider.

        Returns:
            True if all specified terms have been accepted, False otherwise
        """
        return self.provider._has_accepted_terms(terms_or_collection)

    @final
    def accept_terms(self, terms_or_collection: LegalTerms | LegalTermsCollection) -> None:
        """Record acceptance of terms of the provider.

        Args:
            terms_or_collection: Terms to accept
        """
        self.provider._accept_terms(terms_or_collection)

    @final
    @property
    def servers(self) -> list[ServerInfo]:
        """Get list of available servers using the provider.

        Returns:
            List of server information objects.
        """
        if not self.has_accepted_terms():
            raise LegalAcceptanceError("You must accept all legal terms before using the service.")
        return self.provider._servers

    @final
    @property
    def name(self) -> str:
        """Get the name of the provider.

        Returns:
            Provider name as a string.
        """
        return self.provider_name

    @final
    @property
    def version(self) -> Version:
        """Get the version of the provider.

        Returns:
            Provider version as a Version object.
        """
        return self.provider._version

    @final
    @property
    def description(self) -> list[str]:
        """Get the description of the provider.

        Returns:
            Provider description as a list of strings.
        """
        return [
            stripped_line
            for line in self.provider.__doc__.splitlines()  # type: ignore[union-attr]
            if (stripped_line := line.strip())
        ]

    @final
    def measure(
        self, server_id: ServerIDType | None = None, server_host: str | None = None
    ) -> MeasurementResult:
        """Measure network performance using the provider.

        Args:
            server_id: Server ID (integer or string) for test
            server_host: Server hostname for test

        Returns:
            Measurement results

        Raises:
            LegalAcceptanceError: If legal requirements are not accepted
            ValueError: If both server_id and server_host are provided
        """
        # Check legal terms acceptance at the NetVelocimeter level
        if not self.has_accepted_terms():
            raise LegalAcceptanceError("You must accept all legal terms before using the service.")

        if server_id and server_host:
            raise ValueError("Only one of server_id or server_host should be provided.")

        return self.provider._measure(server_id=server_id, server_host=server_host)
