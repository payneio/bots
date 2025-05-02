"""Command execution utilities for the bot."""

import asyncio
import sys
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from rich.console import Console
from rich.prompt import Confirm

from .permissions import CommandPermissions, Permission

console = Console()


class CommandResponse(BaseModel):
    """A response to a command execution."""

    command: str = Field(..., description="The command that was executed")
    output: str = Field(..., description="The output of the command")
    exit_code: int = Field(..., description="The exit code of the command")
    error: Optional[str] = Field(None, description="Error message if the command failed")


class CommandExecutor:
    """Handles command execution with permissions checking."""

    def __init__(self, command_permissions: CommandPermissions, debug=False):
        """Initialize the command executor.

        Args:
            command_permissions: The command permissions configuration
            debug: Whether to print debug information (default: False)
        """
        self.command_permissions = command_permissions
        self.debug = debug

    async def execute_command(self, command: str, auto_approve: bool = False) -> Dict[str, Any]:
        """Execute a shell command with permission checks.

        Args:
            command: The command to execute
            auto_approve: Whether to automatically approve commands that would normally require asking (default: False)

        Returns:
            A dictionary with the command execution results

        Note:
            This returns a dictionary for compatibility with the tool interface.
            For structured access, use get_command_response() which returns CommandResponse.
        """
        if not command or not command.strip():
            return {
                "success": False,
                "output": "",
                "error": "Empty command",
                "exit_code": 1,
                "command": command,
            }

        # Log command
        if self.debug:
            print(f"Command requested: {command}", file=sys.stderr)

        action = self.command_permissions.permit_command(command)

        # Handle the validation result
        if action == Permission.DENY:
            # DENY: Command is explicitly denied
            if self.debug:
                print(f"Command '{command}' is denied by bot permissions", file=sys.stderr)
            return {
                "success": False,
                "output": "",
                "error": f"Command '{command}' is not allowed by bot permissions",
                "exit_code": 1,
                "status": "denied",
                "command": command,
            }
        elif action == Permission.APPROVE:
            # EXECUTE: Command is explicitly allowed - continue to execution below
            if self.debug:
                print(f"Command '{command}' is allowed by bot permissions", file=sys.stderr)
            # We'll proceed to execute this command after this validation block
        elif action == Permission.ASK:
            # ASK: Command requires user approval - ask immediately
            if self.debug:
                print(f"Command '{command}' requires user approval", file=sys.stderr)

            # Auto-approve if specified
            if auto_approve:
                if self.debug:
                    print(f"Auto-approving command: {command}", file=sys.stderr)
                console.print(f"[blue]Auto-approving command:[/blue] {command}")
                # We'll proceed to execute this command after this block
            else:
                console.print(f"\n[yellow]Bot wants to run command:[/yellow] {command}")

                # Ask for approval with a confirmation prompt
                if Confirm.ask("Allow this command?"):
                    # User approved - continue to execution
                    console.print("[green]Command approved - executing...[/green]")
                    # We'll proceed to execute this command after this block
                else:
                    # User denied - return error
                    console.print("\n[red]Command was not approved[/red]")
                    return {
                        "success": False,
                        "output": "",
                        "error": f"Command '{command}' was not approved by the user.",
                        "exit_code": 1,
                        "status": "denied_by_user",
                        "command": command,
                    }
        else:
            # Default case (should not happen, but just in case)
            if self.debug:
                print(f"Command '{command}' has an unknown validation status", file=sys.stderr)
            return {
                "success": False,
                "output": "",
                "error": f"Command '{command}' validation failed",
                "exit_code": 1,
                "status": "denied",
                "command": command,
            }

        # Execute command
        try:
            # Always print the command being executed in light blue
            console.print(f"[blue]Executing: {command}[/blue]")

            if self.debug:
                print(f"Executing command: {command}", file=sys.stderr)

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            # Get results
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr and process.returncode != 0 else None
            exit_code = process.returncode

            if self.debug:
                print(f"Command executed with exit code {exit_code}", file=sys.stderr)
                if output and len(output) > 100:
                    print(f"Output (truncated): {output[:100]}...", file=sys.stderr)
                elif output:
                    print(f"Output: {output}", file=sys.stderr)
                if error:
                    print(f"Error: {error}", file=sys.stderr)

            return {
                "success": exit_code == 0,
                "output": output,
                "error": error,
                "exit_code": exit_code,
                "command": command,
            }

        except Exception as e:
            if self.debug:
                print(f"Error executing command: {e}", file=sys.stderr)
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": 1,
                "command": command,
            }

    def get_command_response(self, result: Dict[str, Any]) -> CommandResponse:
        """Convert a command execution result dictionary to a CommandResponse object.

        Args:
            result: Dictionary returned from execute_command

        Returns:
            A structured CommandResponse object
        """
        return CommandResponse(
            command=result.get("command", "unknown"),
            output=result.get("output", ""),
            exit_code=result.get("exit_code", 1),
            error=result.get("error"),
        )
