"""OpenAI provider implementation."""

from typing import AsyncIterator, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

from bots.models import Message, TokenUsage
from bots.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation."""

    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        """Initialize the OpenAI provider.

        Args:
            api_key: The OpenAI API key
            model_name: The model name to use
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name

    async def generate(
        self,
        messages: List[Message],
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, TokenUsage]:
        """Generate a response from the LLM.

        Args:
            messages: The conversation history
            system_prompt: The system prompt
            temperature: The sampling temperature
            max_tokens: The maximum number of tokens to generate

        Returns:
            The generated text and token usage
        """
        # Convert messages to the OpenAI format
        openai_messages: List[Dict[str, str]] = []

        # Add system prompt
        openai_messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        for message in messages:
            openai_messages.append({"role": message.role.value, "content": message.content})

        # Generate response
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Extract text from response
        text = response.choices[0].message.content or ""

        # Extract token usage
        usage = response.usage
        if usage is not None:
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
        else:
            token_usage = TokenUsage()

        return text, token_usage

    async def generate_stream(
        self,
        messages: List[Message],
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[tuple[str, Optional[TokenUsage]]]:
        """Generate a streaming response from the LLM.

        Args:
            messages: The conversation history
            system_prompt: The system prompt
            temperature: The sampling temperature
            max_tokens: The maximum number of tokens to generate

        Yields:
            Chunks of generated text and token usage (if available)
        """
        # Convert messages to the OpenAI format
        openai_messages: List[Dict[str, str]] = []

        # Add system prompt
        openai_messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        for message in messages:
            openai_messages.append({"role": message.role.value, "content": message.content})

        # Generate streaming response
        stream = await self.client.chat.completions.create(
            model=self.model_name,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content, None

        # Final yield with a None token usage, as streaming doesn't provide token counts
        # In a real implementation, you would estimate token usage
        yield "", TokenUsage()

    @staticmethod
    def get_provider_name() -> str:
        """Get the name of the provider."""
        return "openai"
