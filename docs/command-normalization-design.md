# Command Normalization and Enhanced Permissions

This document outlines a design for improving the command validation system in the bot project with command normalization and more flexible permission specifications.

## Current State

Currently, our permission system has:
- Simple allow/deny lists of command names (base commands only)
- An ask_if_unspecified flag for handling unlisted commands
- No normalization or caching of user decisions

### Limitations

1. We can only allow/deny entire command types, not specific variants with arguments
2. Each command approval is one-time only; users must re-approve similar commands
3. No way to specify patterns or wildcards for permissions
4. Simple string matching doesn't account for shell syntax variations

## Proposed Design

### 1. Command Normalization

We'll add a `normalize_command` function that produces a canonical representation of a command, handling compound commands with pipes, redirections, and other shell operators:

```python
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
                            'via_bash': True
                        })
                    else:
                        normalized_components.append({
                            'command': "bash",
                            'args': parsed[1:]
                        })
                except:
                    # If parsing fails, treat entire bash -c as one command
                    normalized_components.append({
                        'command': "bash",
                        'args': parsed[1:]
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


def _is_in_quotes(string: str, position: int) -> bool:
    """Check if a position in a string is inside quotes."""
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
```

### 2. Updated Permission Specification Format

We'll enhance the permission model while keeping a clean, simple format:

```python
class CommandPermissions(BaseModel):
    """Command permissions configuration."""
    
    # Enhanced allow/deny lists with pattern support
    allow: List[str] = Field(
        default_factory=list, 
        description="Commands the bot can run freely. Format: 'command' or 'command:arg_pattern'"
    )
    deny: List[str] = Field(
        default_factory=list, 
        description="Commands the bot is explicitly blocked from running. Format: 'command' or 'command:arg_pattern'"
    )
    
    # Default behavior
    ask_if_unspecified: bool = Field(
        default=True, 
        description="Ask for permission for unspecified commands"
    )
    
    # Session cache of approved commands
    _approved_commands: Dict[str, bool] = PrivateAttr(default_factory=dict)
    
    def _parse_pattern(self, pattern: str) -> Tuple[str, Optional[str]]:
        """Parse a pattern string into command and args_pattern.
        
        Format: 'command' or 'command:arg_pattern'
        """
        if ":" not in pattern:
            return (pattern, None)
        
        command, args_pattern = pattern.split(":", 1)
        return (command, args_pattern)
    
    def validate_command(self, command: str) -> CommandAction:
        """Validate a command against permissions.
        
        For compound commands (with pipes, etc.), we use the most restrictive
        permission of any component.
        """
        # Normalize the command - this returns a list of components
        components = normalize_command(command)
        
        if not components:
            # Empty command
            return CommandAction.ASK if self.ask_if_unspecified else CommandAction.DENY
        
        # For compound commands, we need to check permissions for each component
        component_results = []
        
        for component in components:
            base_cmd = component['command']
            args = component['args']
            args_str = " ".join(args)
            
            # Skip empty commands (like redirections without a command)
            if not base_cmd:
                continue
            
            # Check if previously approved in this session
            command_key = f"{base_cmd}:{args_str}"
            if command_key in self._approved_commands:
                component_results.append(
                    CommandAction.EXECUTE if self._approved_commands[command_key] else CommandAction.DENY
                )
                continue
            
            # Check deny patterns first
            denied = False
            for pattern in self.deny:
                cmd_pattern, args_pattern = self._parse_pattern(pattern)
                
                # Check if base command matches
                if not fnmatch.fnmatch(base_cmd, cmd_pattern):
                    continue
                    
                # If args pattern exists, check args too
                if args_pattern is not None:
                    if fnmatch.fnmatch(args_str, args_pattern):
                        component_results.append(CommandAction.DENY)
                        denied = True
                        break
                else:
                    # No args pattern, just base command match
                    component_results.append(CommandAction.DENY)
                    denied = True
                    break
            
            if denied:
                continue
            
            # Then check allow patterns
            allowed = False
            for pattern in self.allow:
                cmd_pattern, args_pattern = self._parse_pattern(pattern)
                
                # Check if base command matches
                if not fnmatch.fnmatch(base_cmd, cmd_pattern):
                    continue
                    
                # If args pattern exists, check args too
                if args_pattern is not None:
                    if fnmatch.fnmatch(args_str, args_pattern):
                        component_results.append(CommandAction.EXECUTE)
                        allowed = True
                        break
                else:
                    # No args pattern, just base command match
                    component_results.append(CommandAction.EXECUTE)
                    allowed = True
                    break
            
            if allowed:
                continue
            
            # Default to asking for this component
            component_results.append(CommandAction.ASK if self.ask_if_unspecified else CommandAction.DENY)
        
        # Now determine the overall result based on component results
        if not component_results:
            # Empty command or only redirections
            return CommandAction.ASK if self.ask_if_unspecified else CommandAction.DENY
        elif CommandAction.DENY in component_results:
            # If any component should be denied, deny the whole command
            return CommandAction.DENY
        elif CommandAction.ASK in component_results:
            # If any component needs asking, ask for the whole command
            return CommandAction.ASK
        else:
            # All components are allowed
            return CommandAction.EXECUTE
        
    def approve_command(self, command: str, always: bool = False):
        """Mark a command as approved for this session.
        
        Args:
            command: The command string
            always: If True, add to allow list for persistence
        """
        # For compound commands, we approve each component
        components = normalize_command(command)
        
        for component in components:
            base_cmd = component.get('command', '')
            args = component.get('args', [])
            
            # Skip empty commands
            if not base_cmd:
                continue
                
            args_str = " ".join(args)
            command_key = f"{base_cmd}:{args_str}"
            
            # Add to session cache
            self._approved_commands[command_key] = True
            
            # If always, add to allow list for persistence
            if always:
                if args_str:
                    pattern = f"{base_cmd}:{args_str}"
                else:
                    pattern = base_cmd
                    
                if pattern not in self.allow:
                    self.allow.append(pattern)
    
    def deny_command(self, command: str, always: bool = False):
        """Mark a command as denied for this session.
        
        Args:
            command: The command string
            always: If True, add to deny list for persistence
        """
        # For compound commands, we deny each component
        components = normalize_command(command)
        
        for component in components:
            base_cmd = component.get('command', '')
            args = component.get('args', [])
            
            # Skip empty commands
            if not base_cmd:
                continue
                
            args_str = " ".join(args)
            command_key = f"{base_cmd}:{args_str}"
            
            # Add to session cache
            self._approved_commands[command_key] = False
            
            # If always, add to deny list for persistence
            if always:
                if args_str:
                    pattern = f"{base_cmd}:{args_str}"
                else:
                    pattern = base_cmd
                    
                if pattern not in self.deny:
                    self.deny.append(pattern)
```

## Permission Specification Format

Our configuration format will use enhanced allow/deny lists with string patterns for individual commands:

```json
{
  "allow": [
    "ls",
    "cat:*.txt",
    "grep:pattern file.txt",
    "git:status",
    "find:. -name *.py",
    "xargs:grep pattern"
  ],
  "deny": [
    "rm",
    "shutdown",
    "reboot",
    "git:push*",
    "curl:*-X POST*"
  ],
  "ask_if_unspecified": true
}
```

Each entry in the allow/deny lists can be:
- A simple command name: `"ls"` (matches any use of that command)
- A command with argument pattern: `"git:push*"` (matches the command when its arguments match the pattern)

For compound commands (with pipes, redirections, etc.):
- Each component of the compound command is checked individually against the allow/deny lists
- No need to specify entire compound commands in the allow/deny lists
- For example, for `find . -name *.py | xargs grep pattern`:
  - It checks `find` with its arguments against the lists
  - Then checks `xargs` with its arguments against the lists
  - If both are allowed, the whole command is allowed
  - If any is denied, the whole command is denied
  - If any requires asking, the whole command requires asking

The format is clean, readable, and maintains backward compatibility while adding the power of pattern matching.

## User Interaction Flow

1. Bot requests to run a command
2. System normalizes command and checks against permission entries
3. If match found in deny list, command is denied
4. If match found in allow list, command is executed
5. If no match but command was previously approved/denied in this session, use that decision
6. If still no match, ask user for permission
7. User can choose:
   - "Yes" (approve once)
   - "Always" (always approve this command)
   - "No" (deny once)
   - "Never" (always deny this command)
8. For "Always"/"Never" choices, add to allow/deny list and cache decision

## Implementation Phases

### Phase 1: Command Normalization
- Implement `normalize_command` function in utils.py
- Add tests for command normalization

### Phase 2: Enhanced Permission Model
- Update CommandPermissions class with new format
- Add pattern matching support
- Implement session caching
- Update validation logic

### Phase 3: User Interaction
- Update session command approval flow
- Add "Always"/"Never" options
- Implement persistence for approved/denied commands

## Open Questions

1. Should we support regex or stick with simpler glob patterns?
2. How to handle environment variables and variable expansion in commands?
3. Should permissions be persistable between sessions?
4. How to determine the appropriate level of granularity for storing command permissions?
5. Should we provide a way to clear the session cache without restarting?