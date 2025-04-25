"""Session management for bot."""

import asyncio
import datetime
import json
import platform
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

from bots.config import BotConfig
from bots.llm.pydantic_bot import BotLLM
from bots.llm.schemas import CommandResponse
from bots.models import (
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

    def _get_context_info(self) -> str:
        """Generate context information about the bot and environment.

        Returns:
            A formatted string with context information
        """
        current_time = datetime.datetime.now()
        formatted_date = current_time.strftime("%Y-%m-%d")
        formatted_time = current_time.strftime("%H:%M:%S")

        # Get system information
        system_info = platform.system()
        system_version = platform.version()

        # Get bot configuration information
        config_dir = self.session_path.parent.parent
        model_info = f"{self.config.model_provider}/{self.config.model_name}"

        context = f"""
## Session Context:
- Date: {formatted_date}
- Time: {formatted_time}
- System: {system_info} {system_version}
- Bot Config Directory: {config_dir}
- Model: {model_info}
"""
        return context

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

    def _log_event(self, event_type: str, details: Optional[Dict[str, Any]] = None) -> None:
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
        self.console.print(f"[light_blue]Executing: {command}[/light_blue]")
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
            # Keep actual return code for test compatibility
            exit_code = 0 if process.returncode == 0 else (process.returncode or 1)
            response = CommandResponse(
                command=command,
                output=output,
                exit_code=exit_code,
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

    # Command validation is now handled exclusively in the execute_command tool

    async def handle_slash_command(self, command: str) -> bool:
        """Handle a slash command from the user.

        Args:
            command: The slash command

        Returns:
            True if the session should continue, False if it should end
        """
        if command == "/help":
            self.console.print("\nAvailable commands:")
            self.console.print("  /help    - Show this help message")
            self.console.print("  /code    - Open bot config directory in VS Code")
            self.console.print("  /exit    - Exit the session")
            return True

        elif command == "/code":
            # Get the bot directory path (parent of the session_path)
            bot_dir = self.session_path.parent.parent

            try:
                # Launch VS Code with the bot config directory
                await asyncio.create_subprocess_shell(
                    f"code {bot_dir}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                self.console.print(
                    f"\n[green]Opening VS Code with bot directory:[/green] {bot_dir}"
                )
                self._log_event("command_edit", {"directory": str(bot_dir)})
            except Exception as e:
                self.console.print(f"\n[red]Error opening VS Code:[/red] {e}")
                self._log_event("command_error", {"command": "/code", "error": str(e)})

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
            # Get system prompt and add context information
            system_prompt = self.llm.system_prompt
            context_info = self._get_context_info()
            enhanced_prompt = f"{system_prompt}\n\n{context_info}"
            self.add_message(MessageRole.SYSTEM, enhanced_prompt)

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

                    # No need to process commands - they're already executed during LLM's thinking phase

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
            # Add system message with context information
            system_prompt = self.llm.system_prompt
            context_info = self._get_context_info()
            enhanced_prompt = f"{system_prompt}\n\n{context_info}"
            self.add_message(MessageRole.SYSTEM, enhanced_prompt)

            # Add user message
            self.add_message(MessageRole.USER, prompt)

            # Generate response
            response, token_usage = await self.llm.generate_response(self.conversation.messages)

            # Update token usage
            self.session_info.token_usage.prompt_tokens += token_usage.prompt_tokens
            self.session_info.token_usage.completion_tokens += token_usage.completion_tokens
            self.session_info.token_usage.total_tokens += token_usage.total_tokens

            # Process commands - this function is deprecated
            # The old handle_command_request function has been removed
            # Command execution is now done in the pydantic-tools execute_command tool
            for _ in response.commands:
                pass  # Commands are already executed during the LLM thinking phase

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
            import sys
            print(f"Error: {e}", file=sys.stderr)
            raise
