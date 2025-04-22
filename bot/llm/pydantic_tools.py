"""Pydantic tools for LLM integration.

This module provides tools for working with pydantic-ai to create
structured outputs from LLM responses.
"""

import os
import sys
from typing import List, Type, TypeVar

import pydantic_ai
from pydantic import BaseModel
from pydantic_ai import Agent

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

    def __init__(self, api_key: str, model_name: str = "gpt-4o", temperature: float = 0.7, debug: bool = False):
        """Initialize the structured output generator.

        Args:
            api_key: The API key to use for the LLM
            model_name: The model to use (default: gpt-4o)
            temperature: The temperature to use (default: 0.7)
            debug: Whether to print debug information (default: False)
            
        Raises:
            Exception: If the agent cannot be initialized
        """
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.debug = debug

        # Set the API key in environment
        os.environ["OPENAI_API_KEY"] = api_key

        # Create the agent - we'll initialize a new one with the correct output_type for each request
        # This matches the pattern in the example code
        model_string = f"openai:{model_name}"
        
        if self.debug:
            print(f"Using pydantic-ai version: {version}", file=sys.stderr)
            print(f"Will use model string: {model_string}", file=sys.stderr)

    async def generate(self, prompt: str, output_type: Type[T]) -> T:
        """Generate a structured output from a prompt asynchronously.

        Args:
            prompt: The prompt to send to the LLM
            output_type: The type of the output to generate

        Returns:
            An instance of the output type
            
        Raises:
            Exception: If the LLM request fails
        """
        # Print verbose debug info if debug is enabled
        if self.debug:
            print(f"Generating response with model={self.model_name}, temp={self.temperature}", file=sys.stderr)
            print(f"Output type: {output_type.__name__}", file=sys.stderr)
            print(f"Prompt length: {len(prompt)} chars", file=sys.stderr)
        
        # Special treatment for BotResponse to make sure the format is clear
        if output_type.__name__ == "BotResponse":
            # Add specific JSON format instructions
            prompt = f"{prompt}\n\nYour response MUST be in valid JSON format with 'reply' and 'commands' fields."
            if self.debug:
                print("Adding explicit JSON formatting instructions", file=sys.stderr)

        # Create an agent with the specific output_type for this request
        model_string = f"openai:{self.model_name}"
        agent = Agent(
            model=model_string,
            output_type=output_type,
            temperature=self.temperature,
            instrument=self.debug  # Only instrument if debug is enabled
        )
        
        # Run the agent
        result = await agent.run(prompt)
        
        if result.output is None:
            if self.debug:
                print(f"Agent result had no output. Raw result: {result}", file=sys.stderr)
            raise ValueError("Agent returned None result")
            
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