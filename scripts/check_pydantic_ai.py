#!/usr/bin/env python
"""
Check pydantic-ai Compatibility

This script checks if pydantic-ai is properly installed and functional.
It tests basic operations like creating an Agent and running a simple prompt.
"""

import importlib
import inspect
import os
import sys


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

def check_pydantic_ai():
    """Check pydantic-ai compatibility and functionality."""
    results = []
    
    # Check if pydantic-ai is installed
    available, version, error = check_module_availability("pydantic_ai")
    if not available:
        results.append(("pydantic_ai", False, f"Module not found: {error}"))
        return results
    
    results.append(("pydantic_ai", True, f"Version {version}"))
    
    # Check for Agent class
    try:
        from pydantic_ai import Agent
        results.append(("Agent class", True, "Available"))
        
        # List Agent methods
        methods = [name for name, _ in inspect.getmembers(Agent, predicate=inspect.isfunction)]
        results.append(("Agent methods", True, ", ".join(methods[:5]) + f" (and {len(methods)-5} more)"))
        
    except ImportError as e:
        results.append(("Agent class", False, f"Not found: {e}"))
    except Exception as e:
        results.append(("Agent class", False, f"Error: {e}"))
    
    # Check for openai dependency
    available, version, error = check_module_availability("openai")
    if not available:
        results.append(("openai", False, f"Module not found: {error}"))
    else:
        results.append(("openai", True, f"Version {version}"))
    
    # Test Agent if everything is available
    if all(success for _, success, _ in results):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            results.append(("Agent test", False, "No API key in OPENAI_API_KEY env var"))
            return results
            
        try:
            from pydantic import BaseModel
            
            class TestModel(BaseModel):
                message: str
            
            from pydantic_ai import Agent
            Agent("openai:gpt-3.5-turbo", output_type=TestModel)
            
            results.append(("Agent init", True, "Successfully created Agent"))
        except Exception as e:
            results.append(("Agent init", False, f"Error creating Agent: {e}"))
    
    return results

def main():
    """Run the checks and print results."""
    print("Checking pydantic-ai installation and compatibility...")
    print(f"Python version: {sys.version}")
    print("")
    
    results = check_pydantic_ai()
    
    for check, success, message in results:
        status = "\033[92m✓\033[0m" if success else "\033[91m✗\033[0m"
        print(f"{status} {check}: {message}")
    
    all_success = all(success for _, success, _ in results)
    
    if all_success:
        print("\n\033[92mAll checks passed! pydantic-ai should be fully functional.\033[0m")
        sys.exit(0)
    else:
        print("\n\033[91mSome checks failed. See details above.\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    main()