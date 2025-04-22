"""Base provider interface."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional

from bot.models import Message, TokenUsage


class BaseProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, TokenUsage]:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Message],
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[tuple[str, Optional[TokenUsage]]]:
        """Generate a streaming response from the LLM."""
        pass

    @staticmethod
    @abstractmethod
    def get_provider_name() -> str:
        """Get the name of the provider."""
        pass
