#!/usr/bin/env python
"""
Script to demonstrate how to use Pydantic AI's message format with our bot framework.

This script shows how to:
1. Create messages in Pydantic AI format
2. Pass message history to an agent
3. Retrieve and use messages from the result
"""

import asyncio
import os
import sys
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessagesTypeAdapter

# Add the parent directory to sys.path to import bot modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bots.llm.pydantic_bot import PydanticBotResponse as BotResponse


async def test_messages():
    """Test Pydantic AI message format."""
    print("\n" + "=" * 60)
    print(" Testing Pydantic AI message format")
    print("=" * 60)

    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    # Create an agent
    agent = Agent("openai:gpt-4o", output_type=BotResponse)

    # Create messages - first conversation turn
    print("\nSending first message...")
    result1 = await agent.run("Tell me about Python programming.", api_key=api_key)
    print(f"Response: {result1.output.reply[:100]}...")

    # Get message history from the first result
    messages = result1.new_messages()
    print(f"\nMessage history length: {len(messages)}")
    for i, msg in enumerate(messages):
        print(f"Message {i + 1} kind: {msg.kind}")

    # Continue the conversation with message history
    print("\nSending follow-up message with history...")
    result2 = await agent.run(
        "What are some popular Python web frameworks?", message_history=messages, api_key=api_key
    )
    print(f"Response: {result2.output.reply[:100]}...")

    # Get all messages
    all_messages = result2.all_messages()
    print(f"\nAll messages length: {len(all_messages)}")

    # Serialize and deserialize messages
    print("\nSerializing messages...")
    serialized = ModelMessagesTypeAdapter.dump_json(all_messages)
    print(f"Serialized length: {len(serialized)} bytes")

    # Deserialize
    print("Deserializing messages...")
    deserialized = ModelMessagesTypeAdapter.validate_json(serialized)
    print(f"Deserialized length: {len(deserialized)}")

    # Create a new conversation with the loaded messages
    print("\nUsing deserialized message history...")
    result3 = await agent.run(
        "Compare Django and Flask", message_history=deserialized, api_key=api_key
    )
    print(f"Response: {result3.output.reply[:100]}...")


if __name__ == "__main__":
    asyncio.run(test_messages())
