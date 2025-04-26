"""LLM integration using pydantic-ai for structured output generation."""

import sys
from typing import List, Optional, Tuple

from bots.config import BotConfig, load_system_prompt
from bots.llm.pydantic_tools import BotResponse as PydanticBotResponse
from bots.llm.pydantic_tools import StructuredOutputGenerator
from bots.llm.schemas import BotResponse, CommandAction
from bots.models import Message, MessageRole, TokenUsage
from bots.utils import validate_command


class BotLLM:
    """LLM integration for the bot using pydantic-ai exclusively."""

    def __init__(self, config: BotConfig, debug: bool = False):
        """Initialize the LLM integration.

        Args:
            config: The bot configuration
            debug: Whether to print debug information (default: False)

        Raises:
            ValueError: If the API key is not found or pydantic-ai initialization fails
        """
        self.config = config
        self.api_key = config.resolve_api_key()
        self.debug = debug

        if not self.api_key:
            raise ValueError(f"API key not found for provider: {config.model_provider}")

        # Load system prompt
        self.system_prompt = load_system_prompt(config)

        # Print API key debug info only if debug is enabled
        if self.debug:
            print(
                f"API key for {config.model_provider} is available ({len(self.api_key)} chars)",
                file=sys.stderr,
            )

        # Initialize the structured output generator with command permissions
        try:
            self.structured_generator = StructuredOutputGenerator(
                api_key=self.api_key,
                model_name=config.model_name,
                temperature=config.temperature,
                command_permissions=config.command_permissions,
                debug=self.debug,
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize pydantic-ai: {e}") from e

    def _get_role_name(self, role: MessageRole) -> str:
        """Get the role name as a string.

        Args:
            role: The message role

        Returns:
            The role name as a string
        """
        if role == MessageRole.USER:
            return "User"
        elif role == MessageRole.ASSISTANT:
            return "Assistant"
        elif role == MessageRole.SYSTEM:
            return "System"
        else:
            return "User"

    def _messages_to_prompt(self, messages: List[Message]) -> str:
        """Convert a list of messages to a prompt string.

        Args:
            messages: The messages to convert

        Returns:
            A prompt string with clear instructions for structured output
        """
        # Extract the conversation history
        conversation_parts: List[str] = []

        for message in messages:
            role_prefix = f"{self._get_role_name(message.role)}: "
            conversation_parts.append(f"{role_prefix}{message.content}")

        conversation_history = "\n\n".join(conversation_parts)

        # Add explicit instructions for structured output and command tool
        prompt = f"""
{conversation_history}

Please respond.

YOUR RESPONSE MUST BE IN THIS JSON FORMAT:
{{
  "reply": "Your detailed response to the user, including command outputs"
}}

IMPORTANT: This is for a pydantic schema with:
- reply: string (required)
"""
        return prompt

    async def generate_response(
        self,
        messages: List[Message],
        context: Optional[str] = None,
    ) -> Tuple[BotResponse, TokenUsage]:
        """Generate a response from the LLM.

        This method uses the pydantic-ai structured output generator exclusively.

        Args:
            messages: The conversation history
            context: Optional additional context

        Returns:
            The response and token usage

        Raises:
            ValueError: If the response generation fails
        """

        # Create a prompt from the messages
        prompt = self._messages_to_prompt(messages)

        # Add context if provided
        if context:
            prompt += f"\n\nContext: {context}"

        # Generate structured response
        try:
            structured_response = await self.structured_generator.generate(
                prompt=prompt, output_type=PydanticBotResponse
            )

            # Convert structured response to BotResponse
            bot_response = structured_response.to_schema_response()
            if self.debug:
                print("Response successfully generated and converted", file=sys.stderr)
        except Exception as e:
            # Let the error propagate to the caller
            raise ValueError(f"Failed to generate a structured response: {e}") from e

        # Estimate token usage
        prompt_tokens = len(prompt) // 4
        completion_tokens = len(structured_response.reply) // 4

        token_usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

        return bot_response, token_usage

    async def generate_stream(
        self,
        messages: List[Message],
        context: Optional[str] = None,
    ):
        """Generate a streaming response from the LLM.

        Args:
            messages: The conversation history
            context: Optional additional context

        Yields:
            Partial response objects
        """
        # For now, just generate a complete response and yield it all at once
        # In a future implementation, we can use the streaming API
        response, _ = await self.generate_response(messages, context)
        yield response

    def validate_command(self, command: str) -> CommandAction:
        """Validate a command against the bot's permissions.

        Args:
            command: The command to validate

        Returns:
            The action to take for this command
        """
        return validate_command(
            command=command,
            allow_list=self.config.command_permissions.allow,
            deny_list=self.config.command_permissions.deny,
            ask_if_unspecified=self.config.command_permissions.ask_if_unspecified,
        )
