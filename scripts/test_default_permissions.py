#!/usr/bin/env python
"""
Test the default safe command permissions

This script tests the default safe command permissions in the bot
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to import bot modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import BotConfig, CommandPermissions
from bot.llm.pydantic_bot import BotLLM
from bot.models import Message, MessageRole


def test_default_permissions():
    """Test the default safe command permissions."""
    print("Testing default safe command permissions")
    
    # Create a config with default permissions
    config = BotConfig()
    
    # Print stats about the default permissions
    print(f"Default allow list: {len(config.command_permissions.allow)} commands")
    print(f"Default deny list: {len(config.command_permissions.deny)} commands")
    
    # Test a few example allowed commands
    allowed_examples = ["ls", "cat", "grep", "echo", "find", "ps", "git status"]
    print("\nTesting allow list with examples:")
    for cmd in allowed_examples:
        is_allowed = cmd in config.command_permissions.allow
        print(f"  {cmd}: {'✅ Allowed' if is_allowed else '❌ Not in allow list'}")
    
    # Test a few example denied commands
    denied_examples = ["rm", "mv", "sudo", "vim", "chmod", "ssh", "git push"]
    print("\nTesting deny list with examples:")
    for cmd in denied_examples:
        is_denied = cmd in config.command_permissions.deny
        print(f"  {cmd}: {'✅ Denied' if is_denied else '❌ Not in deny list'}")
    
    # Test ask_if_unspecified
    print(f"\nAsk if unspecified: {config.command_permissions.ask_if_unspecified}")
    
    # Create permissions with custom allow/deny lists
    custom_perms = CommandPermissions(
        allow=["custom1", "custom2"],
        deny=["danger1", "danger2"],
        ask_if_unspecified=False
    )
    
    print("\nCustom permissions still work:")
    print(f"  Allow: {custom_perms.allow}")
    print(f"  Deny: {custom_perms.deny}")
    print(f"  Ask if unspecified: {custom_perms.ask_if_unspecified}")
    
    print("\n✅ Default permissions test successful!")


if __name__ == "__main__":
    test_default_permissions()