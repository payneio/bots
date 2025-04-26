#!/usr/bin/env python
"""
Simple script to run the bot with a predefined message

This script demonstrates running the bot with and without the debug flag
to show how debug output is controlled.
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


async def run_simple_bot(debug: bool = False):
    """Run a simple bot interaction with a predefined message."""
    print(f"\n{'=' * 60}")
    print(f" Running bot with debug={debug}")
    print(f"{'=' * 60}")

    # Create a test config
    config = BotConfig(
        model_provider="openai",
        model_name="gpt-4o",
        temperature=0.7,
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    try:
        # Initialize BotLLM
        llm = BotLLM(config, debug=debug)

        # Create test messages
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a helpful CLI assistant."),
            Message(role=MessageRole.USER, content="Hello! What can you do?"),
        ]

        # Generate response
        response, token_usage = await llm.generate_response(messages)

        # Print results
        print("\nResponse from bot:")
        print(f"{response.message[:200]}...")

        print("\nToken usage:")
        print(f"  Prompt tokens: {token_usage.prompt_tokens}")
        print(f"  Completion tokens: {token_usage.completion_tokens}")
        print(f"  Total tokens: {token_usage.total_tokens}")

    except Exception as e:
        print(f"\nError: {e}")


async def main():
    """Run the bot with and without debug mode."""
    # First without debug
    await run_simple_bot(debug=False)

    # Then with debug
    await run_simple_bot(debug=True)


if __name__ == "__main__":
    asyncio.run(main())
