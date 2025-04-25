"""Pydantic tools for LLM integration.

This module provides tools for working with pydantic-ai to create
structured outputs from LLM responses and execute commands.
"""

import asyncio
import os
import sys
from typing import Any, Dict, Type, TypeVar

import pydantic_ai
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from rich.console import Console
from rich.prompt import Confirm

from bots.config import CommandPermissions
from bots.llm.schemas import BotResponse as SchemaBotResponse
from bots.llm.schemas import CommandAction

# Type variable for the output model
T = TypeVar("T", bound=BaseModel)

# Get version information
version = getattr(pydantic_ai, "__version__", "unknown")

console = Console()


class BotResponse(BaseModel):
    """A structured response from the bot."""

    reply: str

    # Add method to convert to schema.BotResponse
    def to_schema_response(self):
        """Convert to schema.BotResponse."""

        return SchemaBotResponse(
            message=self.reply,
            commands=[],  # Commands are now always empty as they're executed during thinking
        )


class StructuredOutputGenerator:
    """Generator for structured outputs from LLM responses using pydantic-ai."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o",
        temperature: float = 0.7,
        command_permissions: CommandPermissions | None = None,
        debug: bool = False,
    ):
        """Initialize the structured output generator.

        Args:
            api_key: The API key to use for the LLM
            model_name: The model to use (default: gpt-4o)
            temperature: The temperature to use (default: 0.7)
            command_permissions: Permissions for command execution (optional)
            debug: Whether to print debug information (default: False)

        Raises:
            Exception: If the agent cannot be initialized
        """
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.debug = debug
        self.command_permissions = command_permissions or CommandPermissions()

        # Set the API key in environment
        os.environ["OPENAI_API_KEY"] = api_key

        # Create the agent - we'll initialize a new one with the correct output_type for each request
        # This matches the pattern in the example code
        model_string = f"openai:{model_name}"

        if self.debug:
            print(f"Using pydantic-ai version: {version}", file=sys.stderr)
            print(f"Will use model string: {model_string}", file=sys.stderr)

    async def generate(self, prompt: str, output_type: Type[T]) -> Any:
        """Generate a structured output from a prompt asynchronously with command tool support.

        Args:
            prompt: The prompt to send to the LLM
            output_type: The type of the output to generate

        Returns:
            An instance of the output type

        Raises:
            Exception: If the LLM request fails
        """
        # No command results to track anymore - they are included in the response text

        # Print verbose debug info if debug is enabled
        if self.debug:
            print(
                f"Generating response with model={self.model_name}, temp={self.temperature}",
                file=sys.stderr,
            )
            print(f"Output type: {output_type.__name__}", file=sys.stderr)
            print(f"Prompt length: {len(prompt)} chars", file=sys.stderr)

        # Special treatment for BotResponse to make sure the format is clear
        if output_type.__name__ == "BotResponse":
            # Add instructions about the execute_command tool and permission system
            tool_instructions = """
You can execute commands using the execute_command tool when needed.

Command permissions:
1. Commands in the 'allow' list can be executed immediately
2. Commands in the 'deny' list will be rejected
3. Other commands require user approval - you should suggest them in your response

Commands you execute should be added to the 'commands' array in your final response.
If a command requires user approval, explain this in your response.
"""
            # Add specific JSON format instructions
            prompt = f"{prompt}\n\n{tool_instructions}\n\nYour response MUST be in valid JSON format with 'reply' and 'commands' fields."
            if self.debug:
                print("Adding tool and JSON formatting instructions", file=sys.stderr)

        # Create an agent with the specific output_type for this request
        model_string = f"openai:{self.model_name}"
        
        # Explicitly create agent with only the arguments it accepts
        agent = Agent(
            model=model_string,
            output_type=output_type,
            temperature=self.temperature,
            instrument=self.debug  # type: ignore # This is actually valid, but pyright doesn't know about it
        )

        # Add the command execution tool
        @agent.tool
        async def execute_command(ctx: RunContext, command: str) -> Dict[str, Any]:  # pragma: no cover
            """Execute a shell command.

            Args:
                ctx: The run context
                command: The command to execute

            Returns:
                A dictionary with the command execution results
            """
            if not command or not command.strip():
                return {
                    "success": False,
                    "output": "",
                    "error": "Empty command",
                    "exit_code": 1,
                }

            # Log command
            if self.debug:
                print(f"Command requested: {command}", file=sys.stderr)

            # Validate command using the CommandPermissions class
            action = self.command_permissions.validate_command(command)

            # Handle the validation result
            if action == CommandAction.DENY:
                # DENY: Command is explicitly denied
                if self.debug:
                    print(f"Command '{command}' is denied by bot permissions", file=sys.stderr)
                return {
                    "success": False,
                    "output": "",
                    "error": f"Command '{command}' is not allowed by bot permissions",
                    "exit_code": 1,
                    "status": "denied",
                }
            elif action == CommandAction.EXECUTE:
                # EXECUTE: Command is explicitly allowed - continue to execution below
                if self.debug:
                    print(f"Command '{command}' is allowed by bot permissions", file=sys.stderr)
                # We'll proceed to execute this command after this validation block
            elif action == CommandAction.ASK:
                # ASK: Command requires user approval - ask immediately
                if self.debug:
                    print(f"Command '{command}' requires user approval", file=sys.stderr)

                console.print(f"\n[yellow]Bot wants to run command:[/yellow] {command}")

                # Ask for approval with a confirmation prompt
                if Confirm.ask("Allow this command?"):
                    # User approved - continue to execution
                    console.print("[green]Command approved - executing...[/green]")
                    # We'll proceed to execute this command after this block
                else:
                    # User denied - return error
                    console.print("\n[red]Command was not approved[/red]")
                    return {
                        "success": False,
                        "output": "",
                        "error": f"Command '{command}' was not approved by the user.",
                        "exit_code": 1,
                        "status": "denied_by_user",
                    }
            else:
                # Default case (should not happen, but just in case)
                if self.debug:
                    print(f"Command '{command}' has an unknown validation status", file=sys.stderr)
                return {
                    "success": False,
                    "output": "",
                    "error": f"Command '{command}' validation failed",
                    "exit_code": 1,
                    "status": "denied",
                }

            # Execute command
            try:
                # Always print the command being executed in light blue
                console.print(f"[blue]Executing: {command}[/blue]")

                if self.debug:
                    print(f"Executing command: {command}", file=sys.stderr)

                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                # Get results
                output = stdout.decode() if stdout else ""
                error = stderr.decode() if stderr and process.returncode != 0 else None
                exit_code = process.returncode

                # No need to store command results anymore - they will be included in the response text

                if self.debug:
                    print(f"Command executed with exit code {exit_code}", file=sys.stderr)
                    if output and len(output) > 100:
                        print(f"Output (truncated): {output[:100]}...", file=sys.stderr)
                    elif output:
                        print(f"Output: {output}", file=sys.stderr)
                    if error:
                        print(f"Error: {error}", file=sys.stderr)

                return {
                    "success": exit_code == 0,
                    "output": output,
                    "error": error,
                    "exit_code": exit_code,
                }

            except Exception as e:
                if self.debug:
                    print(f"Error executing command: {e}", file=sys.stderr)
                return {
                    "success": False,
                    "output": "",
                    "error": str(e),
                    "exit_code": 1,
                }

        # Run the agent
        result = await agent.run(prompt)

        # Type cast to avoid unnecessary comparison warnings
        # We know this can actually be None, despite what the type checker thinks
        if result.output is None:  # type: ignore
            if self.debug:
                print(f"Agent result had no output. Raw result: {result}", file=sys.stderr)
            raise ValueError("Agent returned None result")

        # No need to add commands to the response anymore - the LLM includes them in the text

        if self.debug:
            print(f"Agent response generated successfully: {type(result.output)}", file=sys.stderr)
        return result.output

    def generate_sync(self, prompt: str, output_type: Type[T]) -> Any:
        """Generate a structured output from a prompt synchronously.

        Args:
            prompt: The prompt to send to the LLM
            output_type: The type of the output to generate

        Returns:
            An instance of the output type

        Raises:
            Exception: If the LLM request fails
        """
        # Note: The synchronous version does not support command tools
        # This is because the command execution is async. Use the async generate method
        # instead if you need command tool support.

        if self.debug:
            print("Warning: generate_sync does not support command tools", file=sys.stderr)

        # Special treatment for BotResponse to make sure the format is clear
        if output_type.__name__ == "BotResponse":
            # Add specific JSON format instructions
            prompt = f"{prompt}\n\nYour response MUST be in valid JSON format with 'reply' and 'commands' fields."

        # Create an agent with the specific output_type for this request
        model_string = f"openai:{self.model_name}"
        
        # Explicitly create agent with only the arguments it accepts
        agent = Agent(
            model=model_string,
            output_type=output_type,
            temperature=self.temperature,
            instrument=self.debug  # type: ignore # This is actually valid, but pyright doesn't know about it
        )

        # Run the agent synchronously
        result = agent.run_sync(prompt)

        # Type cast to avoid unnecessary comparison warnings
        # We know this can actually be None, despite what the type checker thinks
        if result.output is None:  # type: ignore
            if self.debug:
                print(f"Agent result had no output. Raw result: {result}", file=sys.stderr)
            raise ValueError("Agent returned None result")

        if self.debug:
            print(f"Agent response generated successfully: {type(result.output)}", file=sys.stderr)
        return result.output
