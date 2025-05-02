"""Session management for bot."""

import asyncio
import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from rich.console import Console

from bots.bot import Bot
from bots.config import DEFAULT_BOT_EMOJI, USER_EMOJI, BotConfig
from bots.models import (
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
        self.bot = Bot(config, debug=debug)
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
            # Initialize empty messages list instead of Conversation
            self.messages: List[ModelMessage] = []
            self.session_log = SessionLog()

            # Save initial session info
            self._save_session_info()
            self._save_messages()
            self._save_session_log()

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

            # Load messages first (most important)
            messages_path = latest_session / "messages.json"
            if messages_path.exists():
                try:
                    with open(messages_path, "rb") as f:
                        # Load and parse the messages file
                        messages_data = f.read()
                        if self.debug:
                            self.console.print(
                                f"[blue]Loading messages data with length: {len(messages_data)}[/blue]"
                            )
                        self.messages = ModelMessagesTypeAdapter.validate_json(messages_data)

                    # Debug the loaded messages if needed
                    if self.debug:
                        self.console.print(f"[green]Loaded {len(self.messages)} messages[/green]")

                    loaded = True
                except Exception as e:
                    # If we can't load messages with the new format, try legacy format
                    if self.debug:
                        self.console.print(
                            f"[yellow]Error loading messages with new format: {e}[/yellow]"
                        )

                    # Check for old conversation.json file
                    conv_path = latest_session / "conversation.json"
                    if conv_path.exists():
                        self.console.print(
                            "[yellow]Attempting to load legacy format conversation[/yellow]"
                        )
                        # We can't load the old format directly, so we'll create an empty messages list
                        # The user will need to start a new conversation
                        self.messages = []
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
            self._save_messages()
            self._save_session_log()

            # Print message count
            self.console.print(f"Loaded {len(self.messages)} messages from previous session")

            return True
        except Exception as e:
            if self.debug:
                self.console.print(f"[red]Error loading previous session: {e}[/red]")
                import traceback

                traceback.print_exc()
            return False

    def _display_conversation_history(self) -> None:
        """Display the conversation history to the user."""
        if not self.messages:
            return

        # Get user and assistant messages only (skip system message)
        user_assistant_messages = []
        for msg in self.messages:
            if msg.kind == "request" and any(part.part_kind == "user-prompt" for part in msg.parts):
                # This is a user message
                for part in msg.parts:
                    if part.part_kind == "user-prompt":
                        user_assistant_messages.append(("user", part.content))
            elif msg.kind == "response":
                # This is an assistant message
                text_parts = [part for part in msg.parts if part.part_kind == "text"]
                if text_parts:
                    # Join all text parts
                    content = " ".join(part.content for part in text_parts)
                    user_assistant_messages.append(("assistant", content))

        if not user_assistant_messages:
            return

        self.console.print("\n[bold]Previous conversation:[/bold]")

        # Display each message in order
        for role, content in user_assistant_messages:
            if role == "user":
                self.console.print(f"\n{USER_EMOJI} {content}")
            elif role == "assistant":
                emoji = self.config.emoji or DEFAULT_BOT_EMOJI
                self.console.print(f"\n[magenta]{emoji} {content}[/magenta]")

    def _save_session_info(self) -> None:
        """Save session info to disk."""
        info_path = self.session_path / "session.json"
        with open(info_path, "w") as f:
            json.dump(self.session_info.model_dump(), f, indent=2, default=str)

    def _save_messages(self) -> None:
        """Save messages to disk using Pydantic AI serialization."""
        messages_path = self.session_path / "messages.json"
        serialized = ModelMessagesTypeAdapter.dump_json(self.messages)
        # dump_json returns bytes, so we need to open the file in binary mode
        with open(messages_path, "wb") as f:
            f.write(serialized)

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

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation using Pydantic AI's format.

        Args:
            role: The role of the message sender ("user", "assistant", "system")
            content: The message content
        """
        if role == "system":
            system_part = SystemPromptPart(content=content)
            message = ModelRequest(parts=[system_part])
        elif role == "user":
            user_part = UserPromptPart(content=content)
            message = ModelRequest(parts=[user_part])
        elif role == "assistant":
            text_part = TextPart(content=content)
            message = ModelResponse(parts=[text_part])
        else:
            # Default to user message for unknown roles
            user_part = UserPromptPart(content=content)
            message = ModelRequest(parts=[user_part])

        self.messages.append(message)
        self.session_info.num_messages += 1

        self._save_messages()
        self._save_session_info()
        self._log_event("message", {"role": role, "length": len(content)})

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
        if self.messages:
            self._display_conversation_history()
        else:
            response, token_usage = await self.bot.generate_welcome_message()
            self.session_info.token_usage.prompt_tokens += token_usage.prompt_tokens
            self.session_info.token_usage.completion_tokens += token_usage.completion_tokens
            self.session_info.token_usage.total_tokens += token_usage.total_tokens
            self.add_message("assistant", response.message)
            self.console.print(f"\n[cyan]{self.config.emoji} {response.message}[/cyan]")

        try:
            while True:
                try:
                    # Get user input - use a simple prompt
                    user_input = input(f"\n{USER_EMOJI} ")

                    # Check if it's a slash command
                    if user_input.startswith("/"):
                        if not await self.handle_slash_command(user_input):
                            break
                        continue

                    # Skip empty messages
                    if not user_input.strip():
                        continue

                    # Add user message to conversation
                    self.add_message("user", user_input)

                    # Generate response
                    response, token_usage = await self.bot.generate_response(self.messages)

                    self.session_info.token_usage.prompt_tokens += token_usage.prompt_tokens
                    self.session_info.token_usage.completion_tokens += token_usage.completion_tokens
                    self.session_info.token_usage.total_tokens += token_usage.total_tokens
                    self.add_message("assistant", response.message)

                    # Display response
                    self.console.print(f"\n[cyan]{self.config.emoji} {response.message}[/cyan]")

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
            self.add_message("user", prompt)

            response, token_usage = await self.bot.generate_response(self.messages)

            self.session_info.token_usage.prompt_tokens += token_usage.prompt_tokens
            self.session_info.token_usage.completion_tokens += token_usage.completion_tokens
            self.session_info.token_usage.total_tokens += token_usage.total_tokens

            print(response.message)
            self.add_message("assistant", response.message)

            # End session
            self.session_info.end_time = datetime.datetime.now()
            self.session_info.status = SessionStatus.COMPLETED
            self._save_session_info()
            self._log_event("session_end")

        except Exception as e:
            self.session_info.end_time = datetime.datetime.now()
            self.session_info.status = SessionStatus.ERROR
            self._save_session_info()
            self._log_event("session_error", {"error": str(e)})
            print(f"Error: {e}", file=sys.stderr)
            raise
