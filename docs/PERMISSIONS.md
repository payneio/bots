# Command Permissions

This document explains how to configure command permissions for your bot. Command permissions control which shell commands your bot can execute.

## Overview

The bot uses a permission system to determine which shell commands it can run:

- **Allow List**: Commands the bot can execute without asking for permission
- **Deny List**: Commands the bot is explicitly forbidden from executing
- **Ask Policy**: For commands not in either list, the bot will ask for permission before executing

## Configuration

Command permissions are configured in the `config.json` file for each bot. Here's an example:

```json
{
  "command_permissions": {
    "allow": ["ls", "echo", "cat:*.txt", "git:status"],
    "deny": ["rm", "shutdown", "sudo"],
    "ask_if_unspecified": true
  }
}
```

### Pattern Format

Command permissions support three formats:

1. **Simple command**: Just the command name with no arguments (e.g., `"ls"`)
2. **Glob patterns**: `"command:argument_pattern"` using glob-style pattern matching
3. **Regex patterns**: Enclosed in slashes, like `"/regex/"`

### Pattern Matching

#### Glob Patterns

For basic pattern matching, you can use glob patterns:

- `"cat:*.txt"` - Allow `cat` only for `.txt` files
- `"git:status"` - Allow only the `git status` command
- `"rm:*-rf*"` - Deny `rm` commands with `-rf` flags
- `"wget:http*"` - Deny `wget` for HTTP URLs

Glob patterns use the standard wildcard characters:
- `*` - Matches any number of characters
- `?` - Matches a single character

#### Regex Patterns

For more advanced matching, you can use regular expressions enclosed in slashes:

- `"/^kubectl|oc$/"` - Match either "kubectl" or "oc" commands
- `"kubectl:/^get|describe$/"` - Match kubectl commands with subcommands "get" or "describe"
- `"/^docker.*/:run"` - Match any docker command that starts with "docker" followed by anything, with subcommand "run"

Regular expressions provide much more powerful matching capabilities when you need more control than simple glob patterns.

## Subcommand Matching

The permission system has special handling for subcommands (like `kubectl get`, `git commit`, etc.). When specifying a pattern like `"kubectl:get"`, it matches any command that:

1. Starts with `kubectl` as the command
2. Has `get` as the first argument (subcommand)
3. May have any number of additional arguments

This means:
- `"kubectl:get"` matches `kubectl get pods`, `kubectl get nodes -o wide`, etc.
- `"kubectl:get pods"` matches `kubectl get pods`, `kubectl get pods -n kube-system`, etc.

This makes it much easier to work with commands that have a subcommand structure.

## Examples

### Allow Examples

```json
"allow": [
  "ls",                  // Allow all ls commands
  "echo:Hello*",         // Allow echo only when starting with "Hello"
  "cat:*.txt",           // Allow cat only for txt files
  "git:status",          // Allow git status command
  "git:log",             // Allow git log command
  "find:* -name *.py",   // Allow find commands for Python files
  "grep:pattern *",      // Allow grep for specific pattern
  "/kube.*/:get",        // Allow any command matching "kube..." with subcommand "get"
  "kubectl:/desc.*/",    // Allow kubectl with subcommands matching regex "desc..."
]
```

### Deny Examples

```json
"deny": [
  "rm",                  // Deny all rm commands
  "rm:*-rf*",            // Deny rm with -rf flag
  "wget:http*",          // Deny wget for HTTP URLs
  "curl:*-X POST*",      // Deny POST requests with curl
  "sudo",                // Deny all sudo commands
  "apt-get:install*",    // Deny apt-get install commands
  "shutdown",            // Deny shutdown command
  "reboot"               // Deny reboot command
]
```

## Compound Commands

For compound commands (using pipes, redirections, etc.), the bot uses the most restrictive permission:

- If any part is denied, the entire command is denied
- If any part requires asking, the entire command requires asking
- Only if all parts are allowed will the command execute without asking

For example:
- `ls | grep pattern` - If both `ls` and `grep` are allowed, this will execute
- `ls | sudo grep pattern` - If `sudo` is denied, this entire command will be denied
- `ls | awk '{print $1}'` - If `awk` is not in either list, this will require asking

## Default Permissions

The bot comes with a set of default safe permissions that allow read-only commands and common utilities while denying potentially destructive commands.

To view the current default permissions, you can run:

```
uv run python scripts/test_default_permissions.py
```

## Runtime Approval

When the bot asks for permission to run a command:

1. You can approve for just that instance
2. Or approve for the duration of the session

Approvals for the session are kept in memory but not persisted to the configuration file.