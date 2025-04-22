"""LLM integration using pydantic-ai."""

import os
from typing import List, Optional

from openai import OpenAI
from pydantic_ai import agent

from bot.config import BotConfig
from bot.llm.schemas import BotResponse, CommandAction
from bot.models import Message, MessageRole, TokenUsage


class BotLLM:
    """LLM integration for the bot."""

    def __init__(self, config: BotConfig):
        """Initialize the LLM integration.

        Args:
            config: The bot configuration
        """
        self.config = config
        self.api_key = config.resolve_api_key()

        if not self.api_key:
            raise ValueError(f"API key not found for provider: {config.model_provider}")

        # Set up OpenAI client
        self.client = OpenAI(api_key=self.api_key)

        # Load system prompt
        self.system_prompt = self._load_system_prompt(config)

        # Configure response model
        self.response_model = BotResponse

    def _load_system_prompt(self, config: BotConfig) -> str:
        """Load the system prompt from the configuration.

        Args:
            config: The bot configuration

        Returns:
            The system prompt
        """
        # If we have a path to a system prompt file, read it
        if hasattr(config, "system_prompt_path") and config.system_prompt_path:
            path = config.system_prompt_path
            if os.path.exists(path):
                with open(path, "r") as f:
                    return f.read()

        # Default system prompt
        return (
            "You are a helpful AI assistant. You can help with various tasks "
            "and answer questions based on your knowledge. When appropriate, "
            "you can run shell commands to help the user accomplish tasks."
        )

    def _convert_messages(self, bot_messages: List[Message]) -> List[dict]:
        """Convert bot Messages to pydantic-ai messages.

        Args:
            bot_messages: The bot messages

        Returns:
            The pydantic-ai formatted messages
        """
        pydantic_ai_messages = []

        # Add system message at the beginning if it doesn't exist
        if not any(m.role == MessageRole.SYSTEM for m in bot_messages):
            pydantic_ai_messages.append({"role": "system", "content": self.system_prompt})

        # Convert all messages
        for message in bot_messages:
            pydantic_ai_messages.append(
                {
                    "role": message.role.value,
                    "content": message.content,
                }
            )

        return pydantic_ai_messages

    async def generate_response(
        self,
        messages: List[Message],
        context: Optional[str] = None,
    ) -> tuple[BotResponse, TokenUsage]:
        """Generate a response from the LLM.

        Args:
            messages: The conversation history
            context: Optional additional context

        Returns:
            The response and token usage
        """
        # Convert messages to pydantic-ai format
        chat_messages = self._convert_messages(messages)

        # Create and execute the agent
        @agent()
        async def bot_agent(message_history: List[dict]) -> dict:
            """Agent that processes messages and returns a structured response.

            Args:
                message_history: The conversation history

            Returns:
                A structured bot response
            """
            # Add context if provided
            user_message = message_history[-1]["content"] if message_history else ""
            if context:
                user_message = f"{user_message}\n\nContext: {context}"
                
            # In a real implementation, we would send these messages to an LLM
            # But for now, return a simple response directly
            return {
                "message": "I'm a bot assistant.",
                "commands": []
            }

        # Generate response
        response_dict = await bot_agent(chat_messages)
        
        # Convert dict to BotResponse
        response = BotResponse(**response_dict)

        # Placeholder for token usage (pydantic-ai doesn't expose this directly)
        # In a real implementation, you would track this separately
        token_usage = TokenUsage(
            prompt_tokens=len(str(chat_messages)) // 4,  # Rough estimate
            completion_tokens=len(str(response)) // 4,  # Rough estimate
            total_tokens=len(str(chat_messages) + str(response)) // 4,  # Rough estimate
        )

        return response, token_usage

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
            Chunks of the response
        """
        # For now, just generate a complete response and yield it all at once
        # since pydantic-ai 0.1.3 has different streaming API
        response, _ = await self.generate_response(messages, context)
        yield response

    def validate_command(self, command: str) -> CommandAction:
        """Validate a command against the bot's permissions.

        Args:
            command: The command to validate

        Returns:
            The action to take for this command
        """
        # Get the base command (first word)
        base_command = command.split()[0] if command else ""

        # Check if command is explicitly allowed
        if base_command in self.config.command_permissions.allow:
            return CommandAction.EXECUTE

        # Check if command is explicitly denied
        if base_command in self.config.command_permissions.deny:
            return CommandAction.DENY

        # Check if we should ask for unspecified commands
        if self.config.command_permissions.ask_if_unspecified:
            return CommandAction.ASK

        # Default to deny
        return CommandAction.DENY
