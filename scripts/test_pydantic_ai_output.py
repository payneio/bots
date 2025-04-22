#!/usr/bin/env python
"""
Test the output from pydantic-ai directly

This script tests pydantic-ai's ability to generate structured output.
"""

import asyncio
import os

from pydantic import BaseModel


class UserDetails(BaseModel):
    """A simple model for testing structured output."""
    name: str
    age: int
    interests: list[str]

async def test_structured_output():
    """Test pydantic-ai's ability to generate structured output."""
    from pydantic_ai import Agent
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    # Initialize the agent
    agent = Agent("openai:gpt-4", output_type=UserDetails)
    
    # Set the prompt
    prompt = """Extract the user details from this text:
    
My name is John Smith, I'm 35 years old, and I enjoy hiking, reading, and photography.
"""

    print(f"Testing structured output with prompt:\n{prompt}")
    
    try:
        # Run the agent
        result = await agent.run(prompt)
        
        # Print the result
        print("\nOutput type:", type(result.output))
        
        if result.output:
            print("\nStructured output:")
            print(f"Name: {result.output.name}")
            print(f"Age: {result.output.age}")
            print(f"Interests: {', '.join(result.output.interests)}")
        else:
            print("\nError: Received None output from agent")
            
        # Print raw result
        print("\nRaw result:", result)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run the tests."""
    await test_structured_output()

if __name__ == "__main__":
    asyncio.run(main())