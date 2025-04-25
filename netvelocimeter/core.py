"""Core functionality for the NetVelocimeter library."""

import inspect
from typing import Any, TypeVar, final

from packaging.version import Version

from .exceptions import LegalAcceptanceError
from .providers.base import BaseProvider, MeasurementResult, ServerIDType, ServerInfo
from .terms import LegalTerms, LegalTermsCategory, LegalTermsCollection

# Map of provider names to provider classes
_PROVIDERS: dict[str, type[BaseProvider]] = {}

B = TypeVar("B", bound=BaseProvider)


def register_provider(name: str, provider_class: type[B]) -> None:
    """Register a provider with the library.

    This function is primarily for internal use and provider developers.

    Args:
        name: Name to register the provider under
        provider_class: Provider class to register
    """
    if not _PROVIDERS:
        # Auto-import providers when first needed
        _discover_providers()

    # validate provider_class
    if not issubclass(provider_class, BaseProvider) or inspect.isabstract(provider_class):
        raise ValueError(
            f"Invalid provider class: {provider_class}. Must be a concrete subclass of BaseProvider."
        )

    # validate name
    name = name.lower()
    if name in _PROVIDERS:
        raise ValueError(f"Provider '{name}' is already registered.")
    if not name.isidentifier():
        raise ValueError(f"Invalid provider name '{name}'. Must be a valid Python identifier.")
    if not provider_class.__doc__:
        raise ValueError(f"Provider class '{provider_class.__name__}' must have a docstring.")
    _PROVIDERS[name] = provider_class


def get_provider(name: str) -> type[BaseProvider]:
    """Get a provider class by name.

    This function allows advanced users to directly access provider classes
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
    if not _PROVIDERS:
        # Auto-import providers when first needed
        _discover_providers()

    name = name.lower()
    if name not in _PROVIDERS:
        raise ValueError(
            f"Provider '{name}' not found. Available providers: {', '.join(_PROVIDERS.keys())}"
        )

    return _PROVIDERS[name]


def list_providers(include_info: bool = False) -> list[str] | list[tuple[str, str]]:
    """Get a list of all available providers.

    Args:
        include_info: If True, returns provider names with their descriptions.
                     If False, returns just the provider names.

    Returns:
        Either a list of provider names, or a list of (name, description) tuples

    Examples:
        # Get just the names
        providers = list_providers()
        print(f"Available providers: {', '.join(providers)}")

        # Get names with descriptions
        for name, description in list_providers(include_info=True):
            print(f"{name}: {description}")
    """
    if not _PROVIDERS:
        # Auto-import providers when first needed
        _discover_providers()

    if include_info:
        return [
            (
                name,
                provider.__doc__.strip().split("\n")[0] if provider.__doc__ else "No description",
            )
            for name, provider in _PROVIDERS.items()
        ]
    else:
        return list(_PROVIDERS.keys())


def _discover_providers() -> None:
    """Automatically discover and register providers."""
    import netvelocimeter.providers.ookla  # noqa: F401
    import netvelocimeter.providers.static  # noqa: F401


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
        self.provider = provider_class(**kwargs)

    @final
    def legal_terms(
        self, category: LegalTermsCategory = LegalTermsCategory.ALL
    ) -> LegalTermsCollection:
        """Get legal terms for the current provider.

        Args:
            category: Category of terms to retrieve. Defaults to ALL.

        Returns:
            Collection of legal terms that match the requested category
        """
        return self.provider.legal_terms(category)

    @final
    def has_accepted_terms(
        self, terms_or_collection: LegalTerms | LegalTermsCollection | None = None
    ) -> bool:
        """Check if the user has accepted the specified terms.

        Args:
            terms_or_collection: Terms to check. If None, checks all legal terms for the current provider.

        Returns:
            True if all specified terms have been accepted, False otherwise
        """
        return self.provider.has_accepted_terms(terms_or_collection)

    @final
    def accept_terms(self, terms_or_collection: LegalTerms | LegalTermsCollection) -> None:
        """Record acceptance of terms.

        Args:
            terms_or_collection: Terms to accept
        """
        self.provider.accept_terms(terms_or_collection)

    @final
    @property
    def servers(self) -> list[ServerInfo]:
        """Get list of available servers.

        Returns:
            List of server information objects.
        """
        if not self.has_accepted_terms():
            raise LegalAcceptanceError("You must accept all legal terms before using the service.")
        return self.provider.servers

    @final
    @property
    def provider_version(self) -> Version:
        """Get the version of the provider.

        Returns:
            Provider version as a Version object.
        """
        return self.provider.version

    @final
    def measure(
        self, server_id: ServerIDType | None = None, server_host: str | None = None
    ) -> MeasurementResult:
        """Measure network performance using the configured provider.

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

        return self.provider.measure(server_id=server_id, server_host=server_host)
