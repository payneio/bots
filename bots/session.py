"""Session management for bot."""

import asyncio
import datetime
import json
import os
import platform
import socket
from pathlib import Path
from typing import Any, Dict, Optional

from liquid import Template
from rich.console import Console

from bots.config import DEFAULT_BOT_EMOJI, USER_EMOJI, BotConfig, load_system_prompt
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


def bot_name_from_path(path: Path) -> str:
    """Extract bot name from its config directory path.

    Args:
        path: Path to the bot config directory

    Returns:
        The name of the bot
    """
    return path.name


class Session:
    """Interactive session with a bot."""

    def __init__(
        self,
        config: BotConfig,
        session_path: Path,
        debug: bool = False,
        continue_session: bool = False,
        latest_session: Optional[Path] = None,
    ):
        """Initialize a session.

        Args:
            config: The bot configuration
            session_path: The path to the session directory
            debug: Whether to print debug information (default: False)
            continue_session: Whether to continue from previous session (default: False)
            latest_session: Path to latest session (if known)
        """
        self.config = config
        self.session_path = session_path
        self.debug = debug
        self.llm = BotLLM(config, debug=debug)
        self.console = Console()

        # Session directory should already exist (created in async_core.py)

        if continue_session and self._load_previous_session(latest_session):
            self.console.print("[blue]Continuing from previous session[/blue]")
        else:
            # Initialize new session data
            self.session_info = SessionInfo(
                model=config.model_name,
                provider=config.model_provider,
            )
            self.conversation = Conversation()
            self.session_log = SessionLog()

            # Save initial session info
            self._save_session_info()
            self._save_conversation()
            self._save_session_log()

    def _refresh_system_prompt(self) -> None:
        """Reload and render the system prompt into the conversation messages."""
        raw = load_system_prompt(self.config)
        template = Template(raw)
        now = datetime.datetime.now()
        formatted_date = now.strftime("%Y-%m-%d")
        formatted_time = now.strftime("%H:%M:%S")
        config_dir = self.session_path.parent.parent
        cwd = self.config.init_cwd or os.getcwd()
        template_vars = {
            "bot": {
                "name": self.config.name or bot_name_from_path(config_dir),
                "emoji": self.config.emoji or DEFAULT_BOT_EMOJI,
                "description": self.config.description or "No description available",
            },
            "date": formatted_date,
            "time": formatted_time,
            "cwd": cwd,
            "config_dir": str(config_dir),
        }
        rendered = template.render(**template_vars)
        context_info = self._get_context_info()
        enhanced = f"{rendered}\n\n{context_info}"

        # Replace existing system message or insert it
        for idx, msg in enumerate(self.conversation.messages):
            if msg.role == MessageRole.SYSTEM:
                self.conversation.messages[idx] = Message(MessageRole.SYSTEM, enhanced)
                break
        else:
            self.conversation.messages.insert(0, Message(MessageRole.SYSTEM, enhanced))

    def _load_previous_session(self, latest_session: Optional[Path] = None) -> bool:
        """Load data from previous session.

        Args:
            latest_session: Path to the latest session (if known)

        Returns:
            True if successfully loaded, False otherwise
        """
        # If latest_session wasn't provided, try to find it
        if latest_session is None:
            from bots.core import find_latest_session

            # Extract bot name from session path (parent folder of sessions)
            bot_dir = self.session_path.parent.parent
            bot_name = bot_dir.name

            # Find latest session
            latest_session = find_latest_session(bot_name)

        if not latest_session:
            if self.debug:
                self.console.print("[yellow]No previous sessions found[/yellow]")
            return False

        self.console.print(f"Found previous session: \n{latest_session}")

        try:
            loaded = False

            # Load conversation first (most important)
            conv_path = latest_session / "conversation.json"
            if conv_path.exists():
                with open(conv_path, "r") as f:
                    # Load and parse the conversation file
                    conversation_data = f.read()
                    if self.debug:
                        self.console.print(
                            f"[blue]Loading conversation data with length: {len(conversation_data)}[/blue]"
                        )
                    self.conversation = Conversation.model_validate_json(conversation_data)

                # Debug the loaded conversation if needed
                if self.debug:
                    self.console.print(
                        f"[green]Loaded {len(self.conversation.messages)} messages[/green]"
                    )

                loaded = True

            # Load session info
            info_path = latest_session / "session.json"
            if info_path.exists():
                with open(info_path, "r") as f:
                    self.session_info = SessionInfo.model_validate_json(f.read())
                loaded = True

            # Load session log
            log_path = latest_session / "log.json"
            if log_path.exists():
                with open(log_path, "r") as f:
                    self.session_log = SessionLog.model_validate_json(f.read())
                loaded = True

            if not loaded:
                return False

            # Update session status to active again
            self.session_info.status = SessionStatus.ACTIVE
            self.session_info.end_time = None

            # Save data to new session directory
            self._save_session_info()
            self._save_conversation()
            self._save_session_log()

            # Print message count
            self.console.print(
                f"Loaded {len(self.conversation.messages)} messages from previous session"
            )

            return True
        except Exception as e:
            if self.debug:
                self.console.print(f"[red]Error loading previous session: {e}[/red]")
                import traceback

                traceback.print_exc()
            return False

    def _display_conversation_history(self) -> None:
        """Display the conversation history to the user."""
        if not self.conversation.messages:
            return

        # Get user and assistant messages only (skip system message)
        messages = [
            msg
            for msg in self.conversation.messages
            if msg.role in (MessageRole.USER, MessageRole.ASSISTANT)
        ]

        if not messages:
            return

        self.console.print("\n[bold]Previous conversation:[/bold]")

        # Display each message in order
        for msg in messages:
            if msg.role == MessageRole.USER:
                self.console.print(f"\n{USER_EMOJI} {msg.content}")
            elif msg.role == MessageRole.ASSISTANT:
                emoji = self.config.emoji or DEFAULT_BOT_EMOJI
                self.console.print(f"\n[magenta]{emoji} {msg.content}[/magenta]")

        self.console.print("\n[bold]---[/bold]")  # Divider between history and new session

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

        # Get environment information
        hostname = socket.gethostname()
        try:
            username = os.getlogin()
        except Exception:
            username = os.environ.get("USER", "unknown")

        # Use bot's initialized CWD if available, otherwise use current CWD
        cwd = self.config.init_cwd if self.config.init_cwd else os.getcwd()
        home_dir = os.path.expanduser("~")
        ip_address = "127.0.0.1"  # Default for security
        try:
            # Try to get a non-loopback IP - just for information, non-critical
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
        except Exception:
            pass

        # Get bot configuration information
        config_dir = self.session_path.parent.parent

        # The backward compatibility code has been removed since tests were updated
        # to look for "Environment Information" instead of "Session Context"

        # Create template variables
        template_vars = {
            "date": formatted_date,
            "time": formatted_time,
            "system": {
                "name": system_info,
                "version": system_version,
                "hostname": hostname,
                "username": username,
                "ip_address": ip_address,
            },
            "paths": {
                "cwd": cwd,
                "home": home_dir,
                "config_dir": str(config_dir),
            },
            "bot": {
                "name": self.config.name or bot_name_from_path(config_dir),
                "emoji": self.config.emoji or DEFAULT_BOT_EMOJI,
                "model_provider": self.config.model_provider,
                "model_name": self.config.model_name,
                "description": self.config.description or "No description available",
            },
        }

        # Template for environment information
        template_str = """
## Environment Information
- Bot: {{ bot.emoji }} {{ bot.name }} - {{ bot.description }}
- Date: {{ date }}
- Time: {{ time }}
- System: {{ system.name }} {{ system.version }}
- Hostname: {{ system.hostname }}
- Username: {{ system.username }}
- IP Address: {{ system.ip_address }}
- Current Working Directory: {{ paths.cwd }}
- Home Directory: {{ paths.home }}
- Bot Config Directory: {{ paths.config_dir }}
- Model: {{ bot.model_provider }}/{{ bot.model_name }}
"""

        # Render template with liquid
        template = Template(template_str)
        return template.render(**template_vars)

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

        # Always display conversation history when continuing a session
        self._display_conversation_history()

        try:
            while True:
                try:
                    # Get user input - use a simple prompt
                    user_input = input(f"\n{USER_EMOJI} ")

                    self._refresh_system_prompt()

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

                    # Display response with emoji
                    emoji = self.config.emoji or DEFAULT_BOT_EMOJI
                    self.console.print(f"\n[magenta]{emoji} {response.message}[/magenta]")

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
            self._refresh_system_prompt()
            self.add_message(MessageRole.USER, prompt)
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
