#!/usr/bin/env python
"""
Test the command tool functionality

This script tests the ability of the bot to execute commands using the command tool.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to import bot modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bots.config import BotConfig
from bots.llm.pydantic_bot import BotLLM
from bots.models import Message, MessageRole


async def test_command_tool():
    """Test the command tool functionality."""
    print("Testing command tool functionality")

    # Create a test config with default safe permissions
    config = BotConfig(
        model_provider="openai",
        model_name="gpt-4o",
        temperature=0.7,
        api_key=os.environ.get("OPENAI_API_KEY"),
        # Using default permissions
    )

    print(f"Created test config with model: {config.model_name}")
    print(f"Allowed commands: {config.command_permissions.allow}")
    print(f"Denied commands: {config.command_permissions.deny}")

    try:
        # Initialize BotLLM with debug mode for testing
        llm = BotLLM(config, debug=True)
        print("Successfully initialized BotLLM")

        # Create test messages
        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content="You are a helpful CLI assistant that can execute commands.",
            ),
            Message(role=MessageRole.USER, content="How many files are in the current directory?"),
        ]

        print("\nGenerating response with messages:")
        for msg in messages:
            print(f"- {msg.role}: {msg.content[:50]}...")

        # Generate response
        response, token_usage = await llm.generate_response(messages)

        # Print results
        print("\nResponse from bot:")
        print(f"{response.message[:200]}...")
        print(f"Commands executed: {len(response.commands)}")

        for i, cmd in enumerate(response.commands):
            print(f"\nCommand {i + 1}: {cmd.command}")
            print(f"Reason: {cmd.reason}")

        print("\nToken usage:")
        print(f"  Prompt tokens: {token_usage.prompt_tokens}")
        print(f"  Completion tokens: {token_usage.completion_tokens}")
        print(f"  Total tokens: {token_usage.total_tokens}")

        # Try with a more complex prompt
        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content="You are a helpful CLI assistant that can execute commands.",
            ),
            Message(
                role=MessageRole.USER,
                content="Find all Python files in the bot directory and count how many imports they have.",
            ),
        ]

        print("\n\nTrying a more complex prompt...")
        print("\nGenerating response with messages:")
        for msg in messages:
            print(f"- {msg.role}: {msg.content[:50]}...")

        # Generate response
        response, token_usage = await llm.generate_response(messages)

        # Print results
        print("\nResponse from bot:")
        print(f"{response.message[:200]}...")
        print(f"Commands executed: {len(response.commands)}")

        for i, cmd in enumerate(response.commands):
            print(f"\nCommand {i + 1}: {cmd.command}")
            print(f"Reason: {cmd.reason}")

        print("\nToken usage:")
        print(f"  Prompt tokens: {token_usage.prompt_tokens}")
        print(f"  Completion tokens: {token_usage.completion_tokens}")
        print(f"  Total tokens: {token_usage.total_tokens}")

        print("\n✅ Command tool test completed!")

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Run the tests."""
    await test_command_tool()


if __name__ == "__main__":
    asyncio.run(main())
