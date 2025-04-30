"""Tests for session management."""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import patch

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)

from bots.bot import BotResponse
from bots.command.permissions import Permission
from bots.config import BotConfig
from bots.models import SessionStatus, TokenUsage
from bots.session import Session


@pytest.fixture
def temp_session_dir():
    """Create a temporary session directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def bot_config():
    """Create a test bot configuration."""
    config = BotConfig(
        model_provider="openai",
        model_name="gpt-4",
        temperature=0.7,
        api_key="test_key",
        command_permissions={
            "allow": ["ls", "echo"],
            "deny": ["rm", "shutdown"],
            "ask_if_unspecified": True,
        },
    )
    return config


@pytest.fixture
def pydantic_messages() -> List[ModelMessage]:
    """Create a sample set of Pydantic AI messages for testing."""
    messages = []

    # System message
    system_part = SystemPromptPart(content="You are a test assistant.")
    messages.append(ModelRequest(parts=[system_part]))

    # User message
    user_part = UserPromptPart(content="Hello")
    messages.append(ModelRequest(parts=[user_part]))

    # Assistant message
    text_part = TextPart(content="Hi there!")
    messages.append(ModelResponse(parts=[text_part]))

    return messages


# Mock Bot for testing - uses Pydantic AI message format
class MockBot:
    """Mock Bot for testing."""

    def __init__(self, config, debug=False):
        self.config = config
        self.debug = debug
        self.system_prompt = "You are a test assistant."
        self.response = BotResponse(
            message="This is a test response.",
            commands=[],
        )
        self.token_usage = TokenUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )

    def create_system_message(self, content: str) -> ModelMessage:
        """Create a system message for testing."""
        system_part = SystemPromptPart(content=content)
        return ModelRequest(parts=[system_part])

    def create_user_message(self, content: str) -> ModelMessage:
        """Create a user message for testing."""
        user_part = UserPromptPart(content=content)
        return ModelRequest(parts=[user_part])

    def create_assistant_message(self, content: str) -> ModelMessage:
        """Create an assistant message for testing."""
        text_part = TextPart(content=content)
        return ModelResponse(parts=[text_part])

    async def generate_response(self, messages, context=None):
        return self.response, self.token_usage

    def validate_command(self, command):
        if command.startswith("ls") or command.startswith("echo"):
            return Permission.APPROVE
        elif command.startswith("rm") or command.startswith("shutdown"):
            return Permission.DENY
        else:
            return Permission.ASK

    async def execute_command_internal(self, command):
        """Mock execution of a command."""
        if command.startswith("echo"):
            return {
                "success": True,
                "output": command.replace("echo", "").strip().strip("'").strip('"'),
                "error": None,
                "exit_code": 0,
            }
        elif command.startswith("ls"):
            return {
                "success": True,
                "output": "file1.txt  file2.txt  file3.txt",
                "error": None,
                "exit_code": 0,
            }
        else:
            return {
                "success": False,
                "output": "",
                "error": f"Command '{command}' is not allowed",
                "exit_code": 1,
            }


@pytest.mark.asyncio
async def test_session_init(temp_session_dir, bot_config):
    """Test session initialization."""
    # Mock the Bot class to avoid pydantic-ai dependency
    with patch("bots.bot.Bot", MockBot):
        # Create session
        session = Session(bot_config, temp_session_dir)

        # Check if session files were created
        assert (temp_session_dir / "session.json").exists()
        assert (
            temp_session_dir / "messages.json"
        ).exists()  # Now using messages.json instead of conversation.json
        assert (temp_session_dir / "log.json").exists()

        # Check initial session state
        assert session.session_info.model == bot_config.model_name
        assert session.session_info.provider == bot_config.model_provider
        assert session.session_info.num_messages == 0
        assert session.session_info.commands_run == 0


@pytest.mark.asyncio
async def test_continue_session(temp_session_dir, bot_config, pydantic_messages):
    """Test continuing from a previous session."""
    # Mock the find_latest_session function
    with patch("bots.core.find_latest_session") as mock_find_latest:
        # Create a previous session directory and files
        prev_session_dir = temp_session_dir.parent / "prev_session"
        prev_session_dir.mkdir(parents=True, exist_ok=True)

        # Create session files in previous session directory
        session_info = {
            "start_time": "2025-04-01T12:00:00",
            "model": "gpt-4",
            "provider": "openai",
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            "num_messages": 3,
            "commands_run": 1,
            "status": "completed",
        }

        # Serialize the pydantic messages
        messages_json = ModelMessagesTypeAdapter.dump_json(pydantic_messages)

        session_log = {"events": []}

        with open(prev_session_dir / "session.json", "w") as f:
            json.dump(session_info, f)
        with open(prev_session_dir / "messages.json", "wb") as f:
            f.write(messages_json)
        with open(prev_session_dir / "log.json", "w") as f:
            json.dump(session_log, f)

        # Mock the find_latest_session to return our previous session
        mock_find_latest.return_value = prev_session_dir

        # Create a new session with continue_session flag
        with patch("bots.bot.Bot", MockBot):
            session = Session(bot_config, temp_session_dir, continue_session=True)

            # Check that previous messages were loaded
            assert len(session.messages) == 3

            # Check first message (system)
            system_msg = session.messages[0]
            assert system_msg.kind == "request"
            system_part = [part for part in system_msg.parts if part.part_kind == "system-prompt"][
                0
            ]
            assert "You are a test assistant" in system_part.content

            # Check second message (user)
            user_msg = session.messages[1]
            assert user_msg.kind == "request"
            user_part = [part for part in user_msg.parts if part.part_kind == "user-prompt"][0]
            assert user_part.content == "Hello"

            # Check third message (assistant)
            assistant_msg = session.messages[2]
            assert assistant_msg.kind == "response"
            text_part = [part for part in assistant_msg.parts if part.part_kind == "text"][0]
            assert text_part.content == "Hi there!"

            # Check that token usage was loaded
            assert session.session_info.token_usage.prompt_tokens == 100
            assert session.session_info.token_usage.completion_tokens == 50
            assert session.session_info.token_usage.total_tokens == 150

            # Check that status was reset to active
            assert session.session_info.status == SessionStatus.ACTIVE
            assert session.session_info.end_time is None


@pytest.mark.asyncio
async def test_add_message(temp_session_dir, bot_config):
    """Test adding messages to the session with Pydantic AI format."""
    with patch("bots.bot.Bot", MockBot):
        session = Session(bot_config, temp_session_dir)

        # Add user message
        session.add_message("user", "Hello, bot!")

        # Check if message was added
        assert len(session.messages) == 1
        assert session.messages[0].kind == "request"
        # Get user part content
        user_part = [part for part in session.messages[0].parts if part.part_kind == "user-prompt"][
            0
        ]
        assert user_part.content == "Hello, bot!"
        assert session.session_info.num_messages == 1

        # Add assistant message
        session.add_message("assistant", "Hello, user!")

        # Check if message was added
        assert len(session.messages) == 2
        assert session.messages[1].kind == "response"
        # Get assistant part content
        text_part = [part for part in session.messages[1].parts if part.part_kind == "text"][0]
        assert text_part.content == "Hello, user!"
        assert session.session_info.num_messages == 2

        # Add system message
        session.add_message("system", "You are a helpful assistant.")

        # Check if message was added
        assert len(session.messages) == 3
        assert session.messages[2].kind == "request"
        # Get system part content
        system_part = [
            part for part in session.messages[2].parts if part.part_kind == "system-prompt"
        ][0]
        assert system_part.content == "You are a helpful assistant."
        assert session.session_info.num_messages == 3


# Command execution is now handled directly via the Bot's execute_command_internal method
# through the execute_command tool, not through a separate method on the Session class


# Command validation and handling have been moved entirely to pydantic_tools.py
# These tests are being removed as part of architectural simplification


@pytest.mark.asyncio
async def test_interactive_session_start(temp_session_dir, bot_config):
    """Test the start of an interactive session."""
    with patch("bots.bot.Bot", MockBot):
        session = Session(bot_config, temp_session_dir)

        # Mock the console.print method to avoid output during test
        with patch("rich.console.Console.print"):
            # Mock the input function to simulate user exit
            with patch("builtins.input", side_effect=["/exit"]):
                await session.start_interactive()

        # Check if system message was added with context information
        assert len(session.messages) >= 1
        # The first message should be a system message (request with system-prompt part)
        assert session.messages[0].kind == "request"
        # Get the system message content
        system_parts = [
            part for part in session.messages[0].parts if part.part_kind == "system-prompt"
        ]
        assert len(system_parts) > 0
        # Check that the system message has content and contains environment info
        assert system_parts[0].content
        assert "Environment Information" in system_parts[0].content


@pytest.mark.asyncio
async def test_handle_slash_command(temp_session_dir, bot_config):
    """Test handling slash commands."""
    with patch("bots.bot.Bot", MockBot):
        session = Session(bot_config, temp_session_dir)

        # Test /help command
        result = await session.handle_slash_command("/help")
        assert result is True  # Session should continue

        # Test /code command (mock subprocess to prevent VS Code from launching)
        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            # Mock subprocess to prevent VS Code from actually launching
            mock_subprocess.return_value = asyncio.Future()
            mock_subprocess.return_value.set_result(None)

            # Call the command handler
            result = await session.handle_slash_command("/code")

            # Check that subprocess would be called with the right command
            mock_subprocess.assert_called_once()
            cmd = mock_subprocess.call_args[0][0]
            assert "code" in cmd
            assert str(temp_session_dir.parent.parent) in cmd

            # Verify the result
            assert result is True  # Session should continue

        # Test /exit command
        result = await session.handle_slash_command("/exit")
        assert result is False  # Session should end

        # Test unknown command
        result = await session.handle_slash_command("/unknown")
        assert result is True  # Session should continue


@pytest.mark.asyncio
async def test_get_context_info(temp_session_dir, bot_config):
    """Test the _get_context_info function."""
    with patch("bots.bot.Bot", MockBot):
        session = Session(bot_config, temp_session_dir)
        context_info = session._get_context_info()  # type: ignore

        # Check that context includes all expected sections
        assert "Environment Information" in context_info
        assert "Date:" in context_info
        assert "Time:" in context_info
        assert "System:" in context_info
        assert "Bot Config Directory:" in context_info
        assert "Model:" in context_info

        # Check that the config directory path is correct
        assert str(temp_session_dir.parent.parent) in context_info

        # Check that the model info is correct
        assert f"{bot_config.model_provider}/{bot_config.model_name}" in context_info


@pytest.mark.asyncio
async def test_message_serialization(temp_session_dir, bot_config, pydantic_messages):
    """Test serializing and deserializing Pydantic AI messages."""
    # Create a session with the mock messages
    with patch("bots.bot.Bot", MockBot):
        session = Session(bot_config, temp_session_dir)
        # Set messages directly
        session.messages = pydantic_messages.copy()

        # Save messages
        session._save_messages()  # type: ignore

        # Check that the messages file was created
        messages_path = temp_session_dir / "messages.json"
        assert messages_path.exists()

        # Read the file content in binary mode
        with open(messages_path, "rb") as f:
            serialized = f.read()

        # Verify the file has content
        assert len(serialized) > 0

        # Deserialize the messages
        deserialized = ModelMessagesTypeAdapter.validate_json(serialized)

        # Verify the deserialized messages match the original
        assert len(deserialized) == len(pydantic_messages)
        # Check the first message kinds match
        assert deserialized[0].kind == pydantic_messages[0].kind
        # For system message, check the content matches
        system_part = [part for part in deserialized[0].parts if part.part_kind == "system-prompt"][
            0
        ]
        assert "You are a test assistant" in system_part.content


@pytest.mark.asyncio
async def test_one_shot_session(temp_session_dir, bot_config):
    """Test one-shot session mode."""
    # Create specific mock response and token usage
    test_response = BotResponse(message="This is a test response.")
    test_token_usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)

    # Use patch.object to mock Bot.generate_response
    async def mock_generate_response(*args, **kwargs):
        return test_response, test_token_usage

    # First initialize the session with the real MockBot
    with patch("bots.bot.Bot", MockBot):
        session = Session(bot_config, temp_session_dir)

        # Then patch the generate_response method on the instance
        with patch.object(session.bot, "generate_response", mock_generate_response):
            # Set up mocks for print function to verify output
            with patch("builtins.print") as mock_print:
                await session.handle_one_shot("Hello, bot!")

            # Check if messages were added properly (system + user + assistant)
            assert len(session.messages) == 3

            # Verify the system message was properly refreshed
            system_msg = session.messages[0]
            assert system_msg.kind == "request"
            # Find the system-prompt part
            system_parts = [part for part in system_msg.parts if part.part_kind == "system-prompt"]
            assert len(system_parts) > 0
            # Check for environment information which should be included in the system prompt
            assert "Environment Information" in system_parts[0].content

            # Verify the user message was added correctly
            user_msg = session.messages[1]
            assert user_msg.kind == "request"
            # Find the user-prompt part
            user_parts = [part for part in user_msg.parts if part.part_kind == "user-prompt"]
            assert len(user_parts) > 0
            # Check the content matches what was sent
            assert user_parts[0].content == "Hello, bot!"

            # Verify the assistant message was added correctly
            assistant_msg = session.messages[2]
            assert assistant_msg.kind == "response"
            # Find the text part in the assistant response
            text_parts = [part for part in assistant_msg.parts if part.part_kind == "text"]
            assert len(text_parts) > 0
            # Verify the response content matches our mock
            assert text_parts[0].content == "This is a test response."

            # Verify the response was printed to stdout
            mock_print.assert_called_once_with("This is a test response.")

            # Verify session was properly completed
            assert session.session_info.end_time is not None
            assert session.session_info.status == SessionStatus.COMPLETED

            # Verify token usage was updated
            assert session.session_info.token_usage.prompt_tokens == 10
            assert session.session_info.token_usage.completion_tokens == 20
            assert session.session_info.token_usage.total_tokens == 30

            # Verify session event was logged
            assert any(event.event_type == "session_end" for event in session.session_log.events)
            assert any(
                event.event_type == "session_start" and event.details.get("mode") == "one_shot"
                for event in session.session_log.events
            )
