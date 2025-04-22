#!/usr/bin/env python
"""
Verify OpenAI API Key

This script checks if the OPENAI_API_KEY environment variable is valid
by making a minimal API call to OpenAI.
"""

import os
import sys

import openai


def verify_openai_key(api_key=None):
    """
    Verify if an OpenAI API key is valid.
    
    Args:
        api_key: The API key to verify. If None, will use OPENAI_API_KEY env var.
        
    Returns:
        A tuple of (bool, str) indicating success/failure and a message.
    """
    # Use provided key or get from environment
    key = api_key or os.environ.get("OPENAI_API_KEY")
    
    if not key:
        return False, "No API key provided or found in OPENAI_API_KEY environment variable"
    
    # Initialize client
    client = openai.OpenAI(api_key=key)
    
    try:
        # Make minimal API call using models.list which is cheap
        models = client.models.list()
        
        # If we get here, the API call succeeded
        model_count = len(models.data)
        return True, f"API key is valid. {model_count} models available."
    
    except openai.AuthenticationError:
        return False, "Authentication failed. The API key is invalid."
    
    except openai.RateLimitError:
        return False, "Rate limit exceeded. This could mean the key is valid but you've hit your quota."
    
    except openai.APIConnectionError:
        return False, "Connection error. Check your internet connection."
    
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def main():
    """Run the verification and print the results."""
    print("Verifying OpenAI API key...")
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\033[91mError: OPENAI_API_KEY environment variable not set\033[0m")
        print("Please set it with: export OPENAI_API_KEY=your_key_here")
        sys.exit(1)
        
    print(f"API key found in environment ({len(api_key)} chars)")
    
    success, message = verify_openai_key(api_key)
    
    if success:
        print(f"\033[92mSuccess: {message}\033[0m")
        sys.exit(0)
    else:
        print(f"\033[91mError: {message}\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()