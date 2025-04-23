"""Session management for bot."""

import asyncio
import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict

from rich.console import Console
from rich.prompt import Confirm

from bot.config import BotConfig
from bot.llm.pydantic_bot import BotLLM
from bot.llm.schemas import CommandAction, CommandRequest, CommandResponse
from bot.models import (
    Conversation,
    Message,
    MessageRole,
    SessionEvent,
    SessionInfo,
    SessionLog,
    SessionStatus,
)


class Session:
    """Interactive session with a bot."""

    def __init__(self, config: BotConfig, session_path: Path, debug: bool = False):
        """Initialize a session.

        Args:
            config: The bot configuration
            session_path: The path to the session directory
            debug: Whether to print debug information (default: False)
        """
        self.config = config
        self.session_path = session_path
        self.debug = debug
        self.llm = BotLLM(config, debug=debug)
        self.console = Console()

        # Initialize session data
        self.session_info = SessionInfo(
            model=config.model_name,
            provider=config.model_provider,
        )
        self.conversation = Conversation()
        self.session_log = SessionLog()

        # Ensure session directory exists
        self.session_path.mkdir(parents=True, exist_ok=True)

        # Save initial session info
        self._save_session_info()
        self._save_conversation()
        self._save_session_log()

    def _save_session_info(self) -> None:
        """Save session info to disk."""
        info_path = self.session_path / "session.json"
        with open(info_path, "w") as f:
            json.dump(self.session_info.model_dump(), f, indent=2, default=str)

    def _save_conversation(self) -> None:
        """Save conversation to disk."""
        conv_path = self.session_path / "conversation.json"
        with open(conv_path, "w") as f:
            json.dump(self.conversation.model_dump(), f, indent=2, default=str)

    def _save_session_log(self) -> None:
        """Save session log to disk."""
        log_path = self.session_path / "log.json"
        with open(log_path, "w") as f:
            json.dump(self.session_log.model_dump(), f, indent=2, default=str)

    def _log_event(self, event_type: str, details: Dict[str, Any] = None) -> None:
        """Log an event in the session.

        Args:
            event_type: The type of event
            details: Additional details about the event
        """
        if details is None:
            details = {}

        event = SessionEvent(event_type=event_type, details=details)
        self.session_log.events.append(event)
        self._save_session_log()

    def add_message(self, role: MessageRole, content: str) -> None:
        """Add a message to the conversation.

        Args:
            role: The role of the message sender
            content: The message content
        """
        message = Message(role=role, content=content)
        self.conversation.messages.append(message)
        self.session_info.num_messages += 1

        self._save_conversation()
        self._save_session_info()
        self._log_event("message", {"role": role.value, "length": len(content)})

    async def execute_command(self, command: str) -> CommandResponse:
        """Execute a shell command.

        Args:
            command: The command to execute

        Returns:
            The command execution results
        """
        self._log_event("command_execute", {"command": command})

        # Display and log the command being executed
        self.console.print(f"[blue]Executing:[/blue] {command}")
        self.add_message(MessageRole.ASSISTANT, f"Executing: {command}")

        try:
            # Run the command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            # Get results
            output = stdout.decode()
            error = stderr.decode() if process.returncode != 0 else None

            # Log the command output in the conversation
            if output:
                self.add_message(MessageRole.ASSISTANT, f"Command output:\n```\n{output}\n```")
            elif error:
                self.add_message(MessageRole.ASSISTANT, f"Command error:\n```\n{error}\n```")
            else:
                self.add_message(MessageRole.ASSISTANT, "Command executed with no output")

            # Log command execution
            self.session_info.commands_run += 1
            self._save_session_info()

            # Create response
            response = CommandResponse(
                command=command,
                output=output,
                exit_code=process.returncode,
                error=error,
            )

            return response

        except Exception as e:
            # Log error
            self._log_event("command_error", {"command": command, "error": str(e)})

            # Create error response
            return CommandResponse(
                command=command,
                output="",
                exit_code=1,
                error=str(e),
            )

    def validate_command(self, command_request: CommandRequest) -> CommandAction:
        """Validate a command against the bot's permissions.

        Args:
            command_request: The command request to validate

        Returns:
            The action to take for this command
        """
        return self.llm.validate_command(command_request.command)

    async def handle_command_request(self, command_request: CommandRequest) -> CommandResponse:
        """Handle a command request from the LLM.

        Args:
            command_request: The command request

        Returns:
            The command response
        """
        action = self.validate_command(command_request)

        if action == CommandAction.EXECUTE:
            # Execute the command without asking
            if command_request.reason:
                self.console.print(f"\n[green]I need to:[/green] {command_request.reason}")
            return await self.execute_command(command_request.command)

        elif action == CommandAction.ASK:
            # For ASK action, we now set a flag to prompt immediately rather than prompting here
            # The actual prompting will happen in the main loop
            self._log_event("command_needs_approval", {"command": command_request.command})
            response = CommandResponse(
                command=command_request.command,
                output="",
                exit_code=1,
                error="This command requires user approval."
            )
            # Add the needs_immediate_approval attribute
            setattr(response, 'needs_immediate_approval', True)
            return response

        else:  # CommandAction.DENY
            # Deny the command
            self._log_event("command_denied", {"command": command_request.command})
            return CommandResponse(
                command=command_request.command,
                output="Command denied by permissions",
                exit_code=1,
                error="This command is not allowed by the bot's permissions",
            )

    async def handle_slash_command(self, command: str) -> bool:
        """Handle a slash command from the user.

        Args:
            command: The slash command

        Returns:
            True if the session should continue, False if it should end
        """
        if command == "/help":
            self.console.print("\nAvailable commands:")
            self.console.print("  /help   - Show this help message")
            self.console.print("  /config - Show current bot configuration")
            self.console.print("  /exit   - Exit the session")
            return True

        elif command == "/config":
            self.console.print("\nBot configuration:")
            config_dict = json.loads(self.config.model_dump_json())
            self.console.print_json(json.dumps(config_dict, indent=2))
            return True

        elif command == "/exit":
            self.console.print("\nExiting session.")
            return False

        else:
            self.console.print(f"\n[red]Unknown command: {command}[/red]")
            return True

    async def start_interactive(self) -> None:
        """Start an interactive session with the bot."""
        self._log_event("session_start", {"mode": "interactive"})

        self.console.print("Starting interactive session with bot")
        self.console.print("Type '/exit' to end the session.")
        self.console.print("Type '/help' for available commands.")

        # Add system message if not present
        if not any(m.role == MessageRole.SYSTEM for m in self.conversation.messages):
            # Get system prompt
            system_prompt = self.llm.system_prompt
            self.add_message(MessageRole.SYSTEM, system_prompt)

        try:
            self.console.print("\nBot is ready for your input!")

            while True:
                try:
                    # Get user input - use a simple prompt
                    user_input = input("\nYou: ")

                    # Check if it's a slash command
                    if user_input.startswith("/"):
                        if not await self.handle_slash_command(user_input):
                            break
                        continue

                    # Skip empty messages
                    if not user_input.strip():
                        continue

                    # Add user message to conversation
                    self.add_message(MessageRole.USER, user_input)

                    # Generate response
                    response, token_usage = await self.llm.generate_response(
                        self.conversation.messages
                    )

                    # Update token usage
                    self.session_info.token_usage.prompt_tokens += token_usage.prompt_tokens
                    self.session_info.token_usage.completion_tokens += token_usage.completion_tokens
                    self.session_info.token_usage.total_tokens += token_usage.total_tokens

                    # Process commands
                    for command_request in response.commands:
                        command_response = await self.handle_command_request(command_request)

                        # Display command output
                        if command_response.exit_code == 0:
                            self.console.print("\n[green]Command output:[/green]")
                            self.console.print(command_response.output)
                        elif hasattr(command_response, 'needs_immediate_approval') and command_response.needs_immediate_approval:
                            # Command needs immediate approval - ask the user right away
                            self.console.print(
                                f"\n[yellow]Bot wants to run command:[/yellow] {command_request.command}"
                            )
                            if command_request.reason:
                                self.console.print(f"[yellow]Reason:[/yellow] {command_request.reason}")
                            
                            if Confirm.ask("Allow this command?"):
                                # User approved - run the command
                                self.console.print("[green]Command approved - executing...[/green]")
                                self._log_event("command_approved", {"command": command_request.command})
                                
                                # Execute the command
                                approved_response = await self.execute_command(command_request.command)
                                
                                # Display the approved command's output
                                if approved_response.exit_code == 0:
                                    self.console.print("\n[green]Command output:[/green]")
                                    self.console.print(approved_response.output)
                                else:
                                    self.console.print(
                                        f"\n[red]Command error (exit code {approved_response.exit_code}):[/red]"
                                    )
                                    self.console.print(approved_response.error or approved_response.output)
                            else:
                                self.console.print("\n[red]Command was not approved[/red]")
                        else:
                            # Regular error
                            self.console.print(
                                f"\n[red]Command error (exit code {command_response.exit_code}):[/red]"
                            )
                            self.console.print(command_response.error or command_response.output)

                    # Display response
                    self.console.print(f"\n[magenta]Bot: {response.message}[/magenta]")

                    # Add assistant message to conversation
                    self.add_message(MessageRole.ASSISTANT, response.message)

                except KeyboardInterrupt:
                    self.console.print("\nExiting session.")
                    break

                except EOFError:
                    self.console.print("\nEOF detected. Exiting session.")
                    break

                except Exception as e:
                    self._log_event("error", {"error": str(e)})
                    self.console.print(f"\n[red]Error: {e}[/red]")

            # End session
            self.session_info.end_time = datetime.datetime.now()
            self.session_info.status = SessionStatus.COMPLETED
            self._save_session_info()
            self._log_event("session_end")

        except Exception as e:
            # Log error and end session
            self.session_info.end_time = datetime.datetime.now()
            self.session_info.status = SessionStatus.ERROR
            self._save_session_info()
            self._log_event("session_error", {"error": str(e)})
            raise

    async def handle_one_shot(self, prompt: str) -> None:
        """Handle a one-shot request.

        Args:
            prompt: The user's prompt
        """
        self._log_event("session_start", {"mode": "one_shot"})

        try:
            # Add system message
            system_prompt = self.llm.system_prompt
            self.add_message(MessageRole.SYSTEM, system_prompt)

            # Add user message
            self.add_message(MessageRole.USER, prompt)

            # Generate response
            response, token_usage = await self.llm.generate_response(self.conversation.messages)

            # Update token usage
            self.session_info.token_usage.prompt_tokens += token_usage.prompt_tokens
            self.session_info.token_usage.completion_tokens += token_usage.completion_tokens
            self.session_info.token_usage.total_tokens += token_usage.total_tokens

            # Process commands
            for command_request in response.commands:
                command_response = await self.handle_command_request(command_request)

                # Log command output (to stderr)
                if command_response.exit_code == 0:
                    print(f"Command output: {command_response.output}", file=os.sys.stderr)
                else:
                    print(
                        f"Command error (exit code {command_response.exit_code}): "
                        f"{command_response.error or command_response.output}",
                        file=os.sys.stderr,
                    )

            # Print response (to stdout)
            print(response.message)

            # Add assistant message to conversation
            self.add_message(MessageRole.ASSISTANT, response.message)

            # End session
            self.session_info.end_time = datetime.datetime.now()
            self.session_info.status = SessionStatus.COMPLETED
            self._save_session_info()
            self._log_event("session_end")

        except Exception as e:
            # Log error and end session
            self.session_info.end_time = datetime.datetime.now()
            self.session_info.status = SessionStatus.ERROR
            self._save_session_info()
            self._log_event("session_error", {"error": str(e)})

            # Print error (to stderr)
            print(f"Error: {e}", file=os.sys.stderr)
            raise
