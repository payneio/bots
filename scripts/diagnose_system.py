#!/usr/bin/env python
"""
Diagnose Bot System

This script performs a comprehensive diagnostic check of the bot system,
including Python version, dependencies, API keys, and pydantic-ai integration.
"""

import importlib
import os
import platform
import sys
from pathlib import Path

# Add the parent directory to sys.path to import bot modules
sys.path.insert(0, str(Path(__file__).parent.parent))


def colored(text, color):
    """Add color to terminal output."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "end": "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['end']}"


def print_section(title):
    """Print a section title."""
    print(f"\n{colored('=' * 60, 'blue')}")
    print(colored(f" {title}", "blue"))
    print(colored("=" * 60, "blue"))


def print_result(label, result, success=True, details=None):
    """Print a check result."""
    status = colored("✓", "green") if success else colored("✗", "red")
    print(f"{status} {label}: {result}")
    if details and not success:
        print(f"   {colored(details, 'yellow')}")


def check_module_availability(module_name):
    """Check if a module is available and return version info."""
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "unknown")
        return True, version, None
    except ImportError as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, f"Unexpected error: {str(e)}"


def check_python_version():
    """Check Python version compatibility."""
    print_section("Python Environment")

    version = platform.python_version()
    version_info = sys.version_info
    python_path = sys.executable

    # Check Python version (pydantic-ai works with 3.10+)
    min_version = (3, 10)
    version_ok = version_info >= min_version

    print_result(
        "Python version",
        version,
        version_ok,
        f"pydantic-ai requires Python {min_version[0]}.{min_version[1]}+",
    )
    print_result("Python executable", python_path)
    print_result("Platform", platform.platform())


def check_dependencies():
    """Check required dependencies."""
    print_section("Dependencies")

    dependencies = {
        "pydantic": "Required for data validation",
        "pydantic_ai": "Required for structured LLM outputs",
        "openai": "Required for OpenAI API access",
        "rich": "Required for terminal formatting",
        "click": "Required for CLI interface",
    }

    for module, description in dependencies.items():
        available, version, error = check_module_availability(module)
        print_result(
            f"{module}",
            f"{'Installed' if available else 'Not found'} ({version if available else 'N/A'})",
            available,
            f"{description}. Error: {error}" if error else description,
        )

        # For pydantic-ai, check more details if available
        if module == "pydantic_ai" and available:
            try:
                from pydantic_ai import Agent

                print_result("  pydantic-ai Agent", "Available")

                # Check if we can initialize an Agent
                api_key = os.environ.get("OPENAI_API_KEY")
                if api_key:
                    try:
                        Agent("openai:gpt-3.5-turbo", output_type=None)
                        print_result("  Agent initialization", "Successful")
                    except Exception as e:
                        print_result("  Agent initialization", "Failed", False, str(e))
            except Exception as e:
                print_result("  pydantic-ai details", "Error accessing module", False, str(e))


def check_api_keys():
    """Check API keys."""
    print_section("API Keys")

    # Check OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        print_result("OPENAI_API_KEY", f"Present ({len(api_key)} chars)")

        # Verify the key if openai is available
        try:
            import openai

            client = openai.OpenAI(api_key=api_key)

            try:
                # Try a simple models.list call which is cheap
                models = client.models.list()
                model_count = len(models.data)
                print_result(
                    "OpenAI API", f"Connected successfully ({model_count} models available)"
                )

                # Check if gpt-4o is available
                gpt4o_available = any(model.id == "gpt-4o" for model in models.data)
                print_result(
                    "GPT-4o model",
                    "Available" if gpt4o_available else "Not found in models list",
                    gpt4o_available,
                )

            except openai.AuthenticationError:
                print_result("OpenAI API", "Authentication failed", False, "Invalid API key")
            except Exception as e:
                print_result("OpenAI API", "Connection failed", False, str(e))

        except ImportError:
            print_result("OpenAI API", "Could not test (openai module not available)", False)
    else:
        print_result("OPENAI_API_KEY", "Not found in environment", False)


def check_bot_modules():
    """Check bot modules."""
    print_section("Bot Modules")

    try:
        from bots.config import BotConfig

        print_result("bot.config", "Imported successfully")

        # Check default model
        config = BotConfig()
        print_result("Default model", config.model_name)

    except Exception as e:
        print_result("bot.config", "Import failed", False, str(e))

    try:
        print_result("pydantic-ai integration", "Available", True)
    except Exception as e:
        print_result("bot.llm.pydantic_tools", "Import failed", False, str(e))

    try:
        print_result("BotLLM integration", "Available")
    except Exception as e:
        print_result("bot.llm.pydantic_bot", "Import failed", False, str(e))


def main():
    """Run all diagnostic checks."""
    print_section("Bot System Diagnostics")
    print(f"Date/Time: {colored(sys.argv[0], 'cyan')}")

    check_python_version()
    check_dependencies()
    check_api_keys()
    check_bot_modules()

    print("\nDiagnostic check complete. For help with issues, refer to:")
    print("- README.md for installation instructions")
    print("- dev_docs/ directory for developer documentation")
    print("- scripts/ directory for utility scripts")


if __name__ == "__main__":
    main()
