#!/usr/bin/env python
"""
Test full bot system with pydantic-ai integration

This script tests the complete bot system end-to-end to verify all components
are working together correctly with the pydantic-ai integration.
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


async def test_full_system():
    """Test the full bot system with pydantic-ai integration."""
    print("Testing full bot system with pydantic-ai integration")
    print(f"Python version: {sys.version}")

    # Check if API key is available
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    print(f"API key found in environment ({len(api_key)} chars)")

    # Create a test config
    config = BotConfig(
        model_provider="openai",
        model_name="gpt-4o",
        temperature=0.7,
        api_key="ENV:OPENAI_API_KEY",
    )

    print(f"Created test config with model: {config.model_name}")

    try:
        # Initialize BotLLM with debug mode for testing
        llm = BotLLM(config, debug=True)
        print("Successfully initialized BotLLM")

        # Create test messages
        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content="You are a helpful CLI assistant that can suggest commands.",
            ),
            Message(
                role=MessageRole.USER, content="How do I list all files in the current directory?"
            ),
        ]

        print("\nGenerating response with messages:")
        for msg in messages:
            print(f"- {msg.role}: {msg.content[:50]}...")

        # Generate response
        response, token_usage = await llm.generate_response(messages)

        # Print results
        print("\nResponse generated successfully!")
        print(f"Message: {response.message[:100]}...")
        print(f"Commands: {len(response.commands)} found")

        for i, cmd in enumerate(response.commands):
            print(f"\nCommand {i + 1}:")
            print(f"  Command: {cmd.command}")
            print(f"  Reason: {cmd.reason}")

        print("\nToken usage:")
        print(f"  Prompt tokens: {token_usage.prompt_tokens}")
        print(f"  Completion tokens: {token_usage.completion_tokens}")
        print(f"  Total tokens: {token_usage.total_tokens}")

        print("\n✅ Full system test successful!")

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Run the tests."""
    await test_full_system()


if __name__ == "__main__":
    asyncio.run(main())
