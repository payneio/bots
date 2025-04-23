"""Utility functions for the bot."""

import shlex
from typing import Any, Dict, List

from bot.llm.schemas import CommandAction


def _is_in_quotes(string: str, position: int) -> bool:
    """Check if a position in a string is inside quotes.
    
    Args:
        string: The string to check
        position: The position to check
        
    Returns:
        True if the position is inside quotes, False otherwise
    """
    in_single_quotes = False
    in_double_quotes = False
    escaped = False
    
    for i, char in enumerate(string):
        if i >= position:
            break
            
        if char == '\\' and not escaped:
            escaped = True
            continue
            
        if char == '"' and not escaped and not in_single_quotes:
            in_double_quotes = not in_double_quotes
        elif char == "'" and not escaped and not in_double_quotes:
            in_single_quotes = not in_single_quotes
            
        escaped = False
        
    return in_single_quotes or in_double_quotes


def split_command(command: str) -> List[Dict[str, Any]]:
    """Split a command into its components.
    
    Handles compound commands with pipes, redirections, etc.
    
    Args:
        command: The command string to split
        
    Returns:
        List of command components, where each component is a dict with:
        - raw_command: The raw command string for this component
        - operator: Optional operator that follows this command (|, &&, ||, etc.)
    """
    # Special handling for compound commands
    compound_operators = ['|', '&&', '||', ';']
    
    # First, try to identify compound commands
    components = []
    current_command = ""
    in_quotes = False
    quote_char = None
    escaped = False
    
    # Simple parsing to split on operators while respecting quotes
    i = 0
    while i < len(command):
        char = command[i]
        
        # Handle escape sequences
        if char == '\\' and not escaped:
            escaped = True
            current_command += char
            i += 1
            continue
            
        # Handle quotes
        if char in ['"', "'"] and not escaped:
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None
                
        # If we're in quotes, just add the character
        if in_quotes:
            current_command += char
            escaped = False
            i += 1
            continue
            
        # Check for operators when not in quotes
        found_operator = False
        for op in compound_operators:
            if command[i:i+len(op)] == op:
                # We found an operator - add the current command and the operator
                if current_command.strip():
                    components.append({
                        'raw_command': current_command.strip(),
                        'operator': op
                    })
                current_command = ""
                found_operator = True
                i += len(op)
                break
                
        if found_operator:
            continue
            
        # No operator, just add the character
        current_command += char
        escaped = False
        i += 1
    
    # Add the last command if any
    if current_command.strip():
        components.append({
            'raw_command': current_command.strip(),
            'operator': None
        })
    
    return components


def normalize_command(command: str) -> List[Dict[str, Any]]:
    """Normalize a command into components.
    
    Handles compound commands, redirections, and shell syntax.
    
    Args:
        command: The command string to normalize
        
    Returns:
        List of command components, where each component is a dict with:
        - command: The base command name
        - args: List of arguments
        - has_redirection: Whether this component includes redirection
        - via_bash: Whether this command is executed via bash -c
    """
    # Special handling for redirections
    redirection_operators = ['>', '>>', '<', '<<', '2>', '2>>', '&>', '&>>']
    
    # First split the command into parts by compound operators
    components = split_command(command)
    normalized_components = []
    
    # Now process each component to extract command and args
    for component in components:
        raw_cmd = component['raw_command']
        
        # Handle redirections within this component
        has_redirection = False
        for redirection in redirection_operators:
            if redirection in raw_cmd and not _is_in_quotes(raw_cmd, raw_cmd.find(redirection)):
                # Split on redirection, keep only the command part
                raw_cmd = raw_cmd.split(redirection, 1)[0].strip()
                has_redirection = True
                break
        
        # Parse the command part
        try:
            parsed = shlex.split(raw_cmd)
            if not parsed:
                continue
                
            # Handle bash -c pattern
            if parsed[0] == "bash" and len(parsed) >= 3 and parsed[1] in ["-c", "-lc"]:
                # Extract the real command from the bash script
                try:
                    script = parsed[2]
                    # Try to handle simple commands in the script
                    script_parts = shlex.split(script)
                    if script_parts:
                        normalized_components.append({
                            'command': script_parts[0],
                            'args': script_parts[1:],
                            'via_bash': True,
                            'has_redirection': has_redirection
                        })
                    else:
                        normalized_components.append({
                            'command': "bash",
                            'args': parsed[1:],
                            'has_redirection': has_redirection
                        })
                except Exception:
                    # If parsing fails, treat entire bash -c as one command
                    normalized_components.append({
                        'command': "bash",
                        'args': parsed[1:],
                        'has_redirection': has_redirection
                    })
            else:
                # Default case: first word is command, rest are args
                normalized_components.append({
                    'command': parsed[0],
                    'args': parsed[1:],
                    'has_redirection': has_redirection
                })
        except Exception:
            # Fallback to simple splitting
            parts = raw_cmd.split()
            if parts:
                normalized_components.append({
                    'command': parts[0],
                    'args': parts[1:] if len(parts) > 1 else [],
                    'has_redirection': has_redirection
                })
    
    return normalized_components


def validate_command(command: str, allow_list: List[str], deny_list: List[str], ask_if_unspecified: bool) -> CommandAction:
    """Validate a command against permission lists.

    Args:
        command: The command to validate
        allow_list: List of allowed command prefixes
        deny_list: List of denied command prefixes
        ask_if_unspecified: Whether to ask for permission for unspecified commands

    Returns:
        The action to take for this command
    """
    # Extract the base command (first word before any spaces or special chars)
    try:
        parsed = shlex.split(command)
        base_command = parsed[0] if parsed else ""
    except Exception:
        # If we can't parse it, just get the first word
        base_command = command.split()[0] if command else ""

    # Check if command is explicitly allowed
    if base_command in allow_list:
        return CommandAction.EXECUTE

    # Check if command is explicitly denied
    if base_command in deny_list:
        return CommandAction.DENY

    # Check if we should ask for unspecified commands
    if ask_if_unspecified:
        return CommandAction.ASK

    # Default to deny
    return CommandAction.DENY