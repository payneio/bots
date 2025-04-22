#!/usr/bin/env python
"""
Test direct integration with the OpenAI API

This script tests creating structured output using the OpenAI API directly,
without going through the pydantic-ai abstraction layer.
"""

import asyncio
import json
import os
from typing import List

import openai
from pydantic import BaseModel


class BotCommandRequest(BaseModel):
    """A command request from the bot to be executed in the user's shell."""
    command: str
    reason: str

class BotResponse(BaseModel):
    """A structured response from the bot."""
    reply: str
    commands: List[BotCommandRequest] = []

async def test_direct_openai():
    """Test creating structured output using OpenAI API directly."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    # Initialize the OpenAI client
    client = openai.OpenAI(api_key=api_key)
    
    # Create a simple prompt
    prompt = """
User: Hello! Can you help me list files in the current directory?

Please respond to the user in a helpful and conversational way.

YOUR RESPONSE MUST BE IN THIS FORMAT:
{
  "reply": "Your detailed response to the user",
  "commands": [
    {
      "command": "Any shell command you want to run",
      "reason": "Explanation of why you want to run this command"
    }
  ]
}

The "commands" list can be empty if no commands are needed.
"""
    
    print(f"Testing OpenAI API with prompt:\n{prompt}")
    
    try:
        # Set up a function-calling request to get structured output
        functions = [{
            "name": "create_bot_response",
            "description": "Creates a response from the bot to the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "reply": {
                        "type": "string",
                        "description": "Your detailed response to the user"
                    },
                    "commands": {
                        "type": "array",
                        "description": "List of commands to execute",
                        "items": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "A shell command to run"
                                },
                                "reason": {
                                    "type": "string",
                                    "description": "Explanation of why this command is being run"
                                }
                            },
                            "required": ["command", "reason"]
                        }
                    }
                },
                "required": ["reply"]
            }
        }]
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            functions=functions,
            function_call={"name": "create_bot_response"}
        )
        
        # Extract response
        function_args = json.loads(response.choices[0].message.function_call.arguments)
        
        # Validate with Pydantic
        bot_response = BotResponse(**function_args)
        
        # Print the response
        print("\nStructured output:")
        print(f"Reply: {bot_response.reply[:100]}...")
        print(f"Commands: {len(bot_response.commands)} found")
        
        for i, cmd in enumerate(bot_response.commands):
            print(f"\nCommand {i+1}:")
            print(f"  Command: {cmd.command}")
            print(f"  Reason: {cmd.reason}")
        
        print("\nRaw function arguments:", function_args)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run the tests."""
    await test_direct_openai()

if __name__ == "__main__":
    asyncio.run(main())