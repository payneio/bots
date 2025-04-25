"""Test for the default permissions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bots.config import CommandPermissions


def main():
    """Test default permissions configuration."""
    # Get default permissions
    permissions = CommandPermissions.default_safe_permissions()

    print("Default permissions:")
    print("-------------------")
    print(f"Allow list: {len(permissions.allow)} commands")
    print(f"Deny list: {len(permissions.deny)} commands")

    # Test basic allowed commands
    basic_commands = [
        "ls -la",
        "cat file.txt",
        "grep pattern file.txt",
        "ps aux",
        "find . -name '*.py'",
    ]

    # Test pattern-matched allowed commands
    pattern_commands = [
        "ls --color=auto",
        "grep -i pattern file.txt",
        "git log --oneline",
        "curl -I https://example.com",
        "jq '.key' file.json",
        "sed 's/foo/bar/' file.txt",
        "ps --forest",
        "head -n 10 file.txt",
        "tail -f log.txt",
    ]

    # Test compound commands
    compound_commands = [
        "ls -la | grep pattern",
        "find . -name '*.py' | xargs grep 'import'",
        "ps aux | grep python | grep -v grep",
        "cat file.txt | head -n 10",
        "git log --oneline | grep 'feat:'",
    ]

    # Test denied commands
    denied_commands = [
        "rm -rf /",
        "shutdown -h now",
        "reboot",
        "apt-get install package",
        "curl -X POST https://api.example.com",
        "sudo apt update",
        "systemctl restart service",
    ]

    # Test commands that should ask for permission
    ask_commands = [
        "npm install package",
        "make install",
        "docker build -t image .",
        "gcc -o program program.c",
        "rm file.txt",  # Simple rm without -r should ask
    ]

    print("\nTesting basic allowed commands:")
    print("------------------------------")
    for cmd in basic_commands:
        action = permissions.validate_command(cmd)
        print(f"{cmd: <40} -> {action.value}")

    print("\nTesting pattern-matched allowed commands:")
    print("---------------------------------------")
    for cmd in pattern_commands:
        action = permissions.validate_command(cmd)
        print(f"{cmd: <40} -> {action.value}")

    print("\nTesting compound commands:")
    print("------------------------")
    for cmd in compound_commands:
        action = permissions.validate_command(cmd)
        print(f"{cmd: <40} -> {action.value}")

    print("\nTesting denied commands:")
    print("-----------------------")
    for cmd in denied_commands:
        action = permissions.validate_command(cmd)
        print(f"{cmd: <40} -> {action.value}")

    print("\nTesting commands that should ask for permission:")
    print("----------------------------------------------")
    for cmd in ask_commands:
        action = permissions.validate_command(cmd)
        print(f"{cmd: <40} -> {action.value}")


if __name__ == "__main__":
    main()
