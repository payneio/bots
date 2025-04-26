"""LLM integration using pydantic-ai for structured output generation."""

import sys
from typing import Any, Dict, List, Optional, Tuple

import pydantic_ai
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from bots.config import BotConfig
from bots.llm.command_executor import CommandExecutor
from bots.llm.schemas import BotResponse
from bots.models import TokenUsage

# Type alias for Pydantic AI's message format
Message = pydantic_ai.messages.ModelMessage


class PydanticBotResponse(BaseModel):
    """A structured response from the bot."""

    reply: str

    # Add method to convert to schema.BotResponse
    def to_schema_response(self):
        """Convert to schema.BotResponse."""

        return BotResponse(
            message=self.reply
        )


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
        messages: List[Message],
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
        # Create an agent with our output type
        agent = Agent(
            model=f"openai:{self.config.model_name}",
            output_type=PydanticBotResponse,
            temperature=self.config.temperature,
            instrument=self.debug,  # Enable instrumentation if debug is on
        )

        # Add the command execution tool
        @agent.tool
        async def execute_command(ctx: RunContext, command: str) -> Dict[str, Any]:
            """Execute a shell command.

            Args:
                ctx: The run context
                command: The command to execute

            Returns:
                The command execution result
            """
            return await self.command_executor.execute_command(command)

        # Add context as the message if provided
        user_message = ""
        if context:
            user_message = f"Context: {context}"

        # Generate structured response using message history
        try:
            result = await agent.run(
                message=user_message, message_history=messages, api_key=self.api_key
            )

            # Get the structured output
            structured_response = result.output

            # Convert to our schema response
            bot_response = structured_response.to_schema_response()
            if self.debug:
                print("Response successfully generated and converted", file=sys.stderr)

            # Store the new messages for potential future use
            new_messages = result.new_messages()
            if self.debug:
                print(f"Generated {len(new_messages)} new messages", file=sys.stderr)
        except Exception as e:
            # Let the error propagate to the caller
            raise ValueError(f"Failed to generate a structured response: {e}") from e

        # Estimate token usage - would be better to get this from the API result
        # but for now we'll keep the same estimation method
        prompt_size = sum(len(str(m)) for m in messages)
        completion_size = len(structured_response.reply)

        token_usage = TokenUsage(
            prompt_tokens=prompt_size // 4,
            completion_tokens=completion_size // 4,
            total_tokens=(prompt_size + completion_size) // 4,
        )

        return bot_response, token_usage

    # Streaming responses can be implemented in the future if needed