#!/usr/bin/env python
"""
Test the bot response model with pydantic-ai

This script tests pydantic-ai's ability to generate structured output
using our BotResponse model.
"""

import asyncio
import os
from typing import List

from pydantic import BaseModel


class BotCommandRequest(BaseModel):
    """A command request from the bot to be executed in the user's shell."""

    command: str
    reason: str


class BotResponse(BaseModel):
    """A structured response from the bot."""

    reply: str
    commands: List[BotCommandRequest] = []


async def test_bot_response():
    """Test pydantic-ai's ability to generate a BotResponse."""
    from pydantic_ai import Agent

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    # Initialize the agent
    agent = Agent("openai:gpt-4", output_type=BotResponse)

    # Set the prompt
    prompt = """Generate a response to the user's message that includes at least one command.
    
User message: How do I list all files in the current directory?

Your response should include:
1. A helpful explanation of how to list files
2. A command to list files with details

Format your response as a friendly message with the command included.
"""

    print(f"Testing bot response with prompt:\n{prompt}")

    try:
        # Run the agent
        result = await agent.run(prompt)

        # Print the result
        print("\nOutput type:", type(result.output))

        if result.output:
            print("\nStructured output:")
            print(f"Reply: {result.output.reply[:100]}...")
            print(f"Number of commands: {len(result.output.commands)}")
            for i, cmd in enumerate(result.output.commands):
                print(f"\nCommand {i + 1}:")
                print(f"  Command: {cmd.command}")
                print(f"  Reason: {cmd.reason}")
        else:
            print("\nError: Received None output from agent")

        # Print raw result
        print("\nRaw result content:", result.output)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Run the tests."""
    await test_bot_response()


if __name__ == "__main__":
    asyncio.run(main())
