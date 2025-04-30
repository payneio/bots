"""LLM integration using pydantic-ai for structured output generation."""

import sys
from typing import Any, Dict, List, Optional, Tuple

import pydantic_ai
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import Usage

from bots.command.executor import CommandExecutor
from bots.config import BotConfig
from bots.models import TokenUsage


class BotResponse(BaseModel):
    """A response from the bot."""

    message: str = Field(..., description="The message to display to the user")


class Bot:
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

        # Initialize command executor
        self.command_executor = CommandExecutor(config.command_permissions, debug=debug)

        if not self.api_key:
            raise ValueError(f"API key not found for provider: {config.model_provider}")

        # Print API key debug info only if debug is enabled
        if self.debug:
            print(
                f"API key for {config.model_provider} is available ({len(self.api_key)} chars)",
                file=sys.stderr,
            )

            # Debug pydantic-ai version info
            version = getattr(pydantic_ai, "__version__", "unknown")
            print(f"Using pydantic-ai version: {version}", file=sys.stderr)
            model_string = f"openai:{config.model_name}"
            print(f"Will use model string: {model_string}", file=sys.stderr)

    # Message creation is done directly in the Session class
    # No need for helper methods here

    # Command execution is handled directly by CommandExecutor

    async def generate_response(
        self,
        messages: List[ModelMessage],
        context: Optional[str] = None,
    ) -> Tuple[BotResponse, TokenUsage]:
        """Generate a response from the LLM using Pydantic AI's message history.

        Args:
            messages: The conversation history in Pydantic AI message format
            context: Optional additional context

        Returns:
            The response and token usage

        Raises:
            ValueError: If the response generation fails
        """

        agent = Agent(
            model=f"openai:{self.config.model_name}",
            temperature=self.config.temperature,
            instrument=self.debug,
        )

        @agent.tool
        async def execute_command(ctx: RunContext, command: str) -> Dict[str, Any]:
            """Execute a shell command.

            Args:
                command: The command to execute

            Returns:
                The command execution result
            """
            return await self.command_executor.execute_command(command)

        user_message = ""
        if context:
            user_message = f"Context: {context}"

        try:
            result: AgentRunResult = await agent.run(
                message=user_message, message_history=messages, api_key=self.api_key
            )
            new_messages = result.new_messages()
            if self.debug:
                print(f"Generated {len(new_messages)} new messages", file=sys.stderr)
        except Exception as e:
            raise ValueError(f"Failed to generate a structured response: {e}") from e

        usage: Usage = result.usage()
        token_usage = TokenUsage(
            prompt_tokens=usage.request_tokens,
            completion_tokens=usage.response_tokens,
            total_tokens=usage.total_tokens,
        )

        response = BotResponse(message=result.output)

        return (response, token_usage)
