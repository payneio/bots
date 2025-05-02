"""LLM integration using pydantic-ai for structured output generation."""

import datetime
import os
import platform
import socket
import sys
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple

import pydantic_ai
from liquid import Template
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import Usage

from bots.command.executor import CommandExecutor
from bots.config import DEFAULT_BOT_EMOJI, BotConfig, load_system_prompt
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

    def instructions(self) -> str:
        """Create a system prompt from the bot's configuration.

        Returns:
            The system prompt as a string
        """
        raw = load_system_prompt(self.config)
        template = Template(raw)
        now = datetime.datetime.now()
        formatted_date = now.strftime("%Y-%m-%d")
        formatted_time = now.strftime("%H:%M:%S")
        cwd = self.config.init_cwd or os.getcwd()
        template_vars = {
            "bot": {
                "name": self.config.name or "Unnamed Bot",
                "emoji": self.config.emoji or DEFAULT_BOT_EMOJI,
                "description": self.config.description or "No description available",
            },
            "date": formatted_date,
            "time": formatted_time,
            "cwd": cwd,
            "disallowed_commands": self.config.command_permissions.deny,
        }
        rendered = template.render(**template_vars)
        context_info = self._get_context_info()
        return f"{rendered}\n\n{context_info}"

    def _get_context_info(self) -> str:
        """Generate context information about the bot and environment.

        Returns:
            A formatted string with context information
        """
        current_time = datetime.datetime.now()
        formatted_date = current_time.strftime("%Y-%m-%d")
        formatted_time = current_time.strftime("%H:%M:%S")

        # Get system information
        system_info = platform.system()
        system_version = platform.version()

        # Get environment information
        hostname = socket.gethostname()
        try:
            username = os.getlogin()
        except Exception:
            username = os.environ.get("USER", "unknown")

        # Use bot's initialized CWD if available, otherwise use current CWD
        cwd = self.config.init_cwd if self.config.init_cwd else os.getcwd()
        home_dir = os.path.expanduser("~")
        ip_address = "127.0.0.1"  # Default for security
        try:
            # Try to get a non-loopback IP - just for information, non-critical
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
        except Exception:
            pass

        template_vars = {
            "date": formatted_date,
            "time": formatted_time,
            "system": {
                "name": system_info,
                "version": system_version,
                "hostname": hostname,
                "username": username,
                "ip_address": ip_address,
            },
            "paths": {
                "cwd": cwd,
                "home": home_dir,
            },
            "bot": {
                "name": self.config.name or "Unnamed Bot",
                "emoji": self.config.emoji or DEFAULT_BOT_EMOJI,
                "model_provider": self.config.model_provider,
                "model_name": self.config.model_name,
                "description": self.config.description or "No description available",
            },
        }

        template_str = dedent("""
            ## Environment Information
            - Bot: {{ bot.emoji }} {{ bot.name }} - {{ bot.description }}
            - Date: {{ date }}
            - Time: {{ time }}
            - System: {{ system.name }} {{ system.version }}
            - Hostname: {{ system.hostname }}
            - Username: {{ system.username }}
            - IP Address: {{ system.ip_address }}
            - Current Working Directory: {{ paths.cwd }}
            - Home Directory: {{ paths.home }}
            - Model: {{ bot.model_provider }}/{{ bot.model_name }}
            """)

        # Render template with liquid
        template = Template(template_str)
        return template.render(**template_vars)

    async def generate_welcome_message(self) -> Tuple[BotResponse, TokenUsage]:
        """Generate a welcome message using LLM and execute any initial actions."""

        agent = Agent(
            model=f"openai:{self.config.model_name}",
            temperature=self.config.temperature,
            instructions=self.instructions(),
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
            return await self.command_executor.execute_command(command, auto_approve=True)

        try:
            user_message = "I am starting a new session with you, Take all actions necessary to gain understanding of your context and to prepare yourself to be ready to talk to me. Don't tell me the results of your actions unless it's important for me to know. Instead, greet me concisely with ONE sentence."
            result: AgentRunResult = await agent.run(message=user_message, api_key=self.api_key)
            new_messages = result.new_messages()
            if self.debug:
                print(f"Generated {len(new_messages)} new messages", file=sys.stderr)
        except Exception as e:
            raise ValueError(f"Failed to generate a structured response: {e}") from e

        response = BotResponse(message=result.output)

        usage: Usage = result.usage()
        token_usage = TokenUsage(
            prompt_tokens=usage.request_tokens,
            completion_tokens=usage.response_tokens,
            total_tokens=usage.total_tokens,
        )

        return (response, token_usage)

    async def generate_response(
        self,
        messages: List[ModelMessage],
        context: Optional[str] = None,
        auto_approve_commands: bool = False,
    ) -> Tuple[BotResponse, TokenUsage]:
        """Generate a response from the LLM using Pydantic AI.

        Args:
            messages: Either a user message string or conversation history in Pydantic AI message format
            context: Optional additional context
            auto_approve_commands: Whether to auto-approve commands that would normally require asking

        Returns:
            The response and token usage

        Raises:
            ValueError: If the response generation fails
        """

        agent = Agent(
            model=f"openai:{self.config.model_name}",
            temperature=self.config.temperature,
            instructions=self.instructions(),
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
            return await self.command_executor.execute_command(
                command, auto_approve=auto_approve_commands
            )

        try:
            user_message = f"Context: {context}" if context else ""
            result: AgentRunResult = await agent.run(
                message=user_message, message_history=messages, api_key=self.api_key
            )
            new_messages = result.new_messages()
            if self.debug:
                print(f"Generated {len(new_messages)} new messages", file=sys.stderr)
        except Exception as e:
            raise ValueError(f"Failed to generate a structured response: {e}") from e

        response = BotResponse(message=result.output)

        usage: Usage = result.usage()
        token_usage = TokenUsage(
            prompt_tokens=usage.request_tokens,
            completion_tokens=usage.response_tokens,
            total_tokens=usage.total_tokens,
        )

        return (response, token_usage)
