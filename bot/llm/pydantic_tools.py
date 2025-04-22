"""Pydantic tools for LLM integration.

This module provides tools for working with pydantic-ai to create
structured outputs from LLM responses and execute commands.
"""

import asyncio
import os
import sys
from typing import Dict, List, Type, TypeVar

import pydantic_ai
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from bot.config import CommandPermissions

# Type variable for the output model
T = TypeVar("T", bound=BaseModel)

# Get version information
version = getattr(pydantic_ai, "__version__", "unknown")


class BotCommandRequest(BaseModel):
    """A command request from the bot to be executed in the user's shell."""

    command: str
    reason: str


class BotResponse(BaseModel):
    """A structured response from the bot."""

    reply: str
    commands: List[BotCommandRequest] = []
    
    # Add method to convert to schema.BotResponse
    def to_schema_response(self):
        """Convert to schema.BotResponse."""
        from bot.llm.schemas import BotResponse as SchemaBotResponse
        from bot.llm.schemas import CommandRequest
        
        return SchemaBotResponse(
            message=self.reply,
            commands=[
                CommandRequest(command=cmd.command, reason=cmd.reason)
                for cmd in self.commands
            ]
        )


class StructuredOutputGenerator:
    """Generator for structured outputs from LLM responses using pydantic-ai."""

    def __init__(
        self, 
        api_key: str, 
        model_name: str = "gpt-4o", 
        temperature: float = 0.7, 
        command_permissions: CommandPermissions = None,
        debug: bool = False
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
        self.command_results = []

        # Set the API key in environment
        os.environ["OPENAI_API_KEY"] = api_key

        # Create the agent - we'll initialize a new one with the correct output_type for each request
        # This matches the pattern in the example code
        model_string = f"openai:{model_name}"
        
        if self.debug:
            print(f"Using pydantic-ai version: {version}", file=sys.stderr)
            print(f"Will use model string: {model_string}", file=sys.stderr)

    async def generate(self, prompt: str, output_type: Type[T]) -> T:
        """Generate a structured output from a prompt asynchronously with command tool support.

        Args:
            prompt: The prompt to send to the LLM
            output_type: The type of the output to generate

        Returns:
            An instance of the output type
            
        Raises:
            Exception: If the LLM request fails
        """
        # Reset command results from any previous run
        self.command_results = []

        # Print verbose debug info if debug is enabled
        if self.debug:
            print(f"Generating response with model={self.model_name}, temp={self.temperature}", file=sys.stderr)
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
        agent = Agent(
            model=model_string,
            output_type=output_type,
            temperature=self.temperature,
            instrument=self.debug,  # Only instrument if debug is enabled
        )
        
        # Add the command execution tool
        @agent.tool
        async def execute_command(ctx: RunContext, command: str) -> Dict:
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

            # Get the base command (first word)
            base_command = command.split()[0] if command else ""

            # Validate command according to our permission model
            if base_command in self.command_permissions.deny:
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
            elif base_command in self.command_permissions.allow:
                # EXECUTE: Command is explicitly allowed - continue to execution below
                if self.debug:
                    print(f"Command '{command}' is allowed by bot permissions", file=sys.stderr)
                # We'll proceed to execute this command after this validation block
            elif self.command_permissions.ask_if_unspecified:
                # ASK: Command requires user approval
                if self.debug:
                    print(f"Command '{command}' requires user approval", file=sys.stderr)
                return {
                    "success": False,
                    "output": "",
                    "error": f"Command '{command}' requires user approval. Please ask the user for permission.",
                    "exit_code": 1,
                    "status": "needs_approval",
                    "command": command,
                }
            else:
                # Default to DENY if not in allow list and ask_if_unspecified is False
                if self.debug:
                    print(f"Command '{command}' is not in the allow list and is denied by default", file=sys.stderr)
                return {
                    "success": False,
                    "output": "",
                    "error": f"Command '{command}' is not in the allowed commands list",
                    "exit_code": 1,
                    "status": "denied",
                }

            # Execute command
            try:
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

                # Store command result for later inclusion in BotResponse
                command_result = {
                    "command": command,
                    "output": output,
                    "error": error,
                    "exit_code": exit_code
                }
                self.command_results.append(command_result)

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
        
        if result.output is None:
            if self.debug:
                print(f"Agent result had no output. Raw result: {result}", file=sys.stderr)
            raise ValueError("Agent returned None result")
            
        # For BotResponse, ensure commands executed are included
        if output_type.__name__ == "BotResponse" and hasattr(result.output, "commands"):
            # Check if there are executed commands that aren't in the response
            existing_commands = {cmd.command for cmd in result.output.commands}
            for cmd_result in self.command_results:
                if cmd_result["command"] not in existing_commands:
                    # Add this command to the response
                    result.output.commands.append(BotCommandRequest(
                        command=cmd_result["command"],
                        reason="Command executed during response generation"
                    ))
                    if self.debug:
                        print(f"Added executed command to response: {cmd_result['command']}", file=sys.stderr)
            
        if self.debug:
            print(f"Agent response generated successfully: {type(result.output)}", file=sys.stderr)
        return result.output
        
    def generate_sync(self, prompt: str, output_type: Type[T]) -> T:
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
        agent = Agent(
            model=model_string,
            output_type=output_type,
            temperature=self.temperature,
            instrument=self.debug  # Only instrument if debug is enabled
        )
        
        # Run the agent synchronously
        result = agent.run_sync(prompt)
        
        if result.output is None:
            if self.debug:
                print(f"Agent result had no output. Raw result: {result}", file=sys.stderr)
            raise ValueError("Agent returned None result")
            
        if self.debug:
            print(f"Agent response generated successfully: {type(result.output)}", file=sys.stderr)
        return result.output