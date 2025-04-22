"""Provider factory for creating LLM providers."""

from typing import Dict, Optional, Type

from bot.config import BotConfig
from bot.providers.base import BaseProvider
from bot.providers.openai_provider import OpenAIProvider


class ProviderFactory:
    """Factory for creating LLM providers."""

    _providers: Dict[str, Type[BaseProvider]] = {
        "openai": OpenAIProvider,
    }

    @classmethod
    def register_provider(cls, provider_name: str, provider_class: Type[BaseProvider]) -> None:
        """Register a new provider.

        Args:
            provider_name: The name of the provider
            provider_class: The provider class
        """
        cls._providers[provider_name] = provider_class

    @classmethod
    def create_provider(cls, config: BotConfig) -> Optional[BaseProvider]:
        """Create a provider from a configuration.

        Args:
            config: The bot configuration

        Returns:
            The provider instance or None if the provider is not found
        """
        provider_name = config.model_provider.lower()

        if provider_name not in cls._providers:
            return None

        provider_class = cls._providers[provider_name]
        api_key = config.resolve_api_key()

        if not api_key:
            raise ValueError(f"API key not found for provider: {provider_name}")

        if provider_name == "openai":
            return OpenAIProvider(api_key=api_key, model_name=config.model_name)

        # Generic case (shouldn't be reached with current providers)
        return provider_class(api_key=api_key)
