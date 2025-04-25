"""Tests for session management."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from bots.config import BotConfig
from bots.llm.schemas import BotResponse, CommandAction
from bots.models import MessageRole, SessionStatus, TokenUsage
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


# Mock BotLLM for testing - avoids pydantic-ai compatibility issues
class MockBotLLM:
    """Mock BotLLM for testing."""

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

    async def generate_response(self, messages, context=None):
        return self.response, self.token_usage

    def validate_command(self, command):
        if command.startswith("ls") or command.startswith("echo"):
            return CommandAction.EXECUTE
        elif command.startswith("rm") or command.startswith("shutdown"):
            return CommandAction.DENY
        else:
            return CommandAction.ASK


@pytest.mark.asyncio
async def test_session_init(temp_session_dir, bot_config):
    """Test session initialization."""
    # Mock the BotLLM class to avoid pydantic-ai dependency
    with patch("bots.session.BotLLM", MockBotLLM):
        # Create session
        session = Session(bot_config, temp_session_dir)

        # Check if session files were created
        assert (temp_session_dir / "session.json").exists()
        assert (temp_session_dir / "conversation.json").exists()
        assert (temp_session_dir / "log.json").exists()

        # Check initial session state
        assert session.session_info.model == bot_config.model_name
        assert session.session_info.provider == bot_config.model_provider
        assert session.session_info.num_messages == 0
        assert session.session_info.commands_run == 0
        
@pytest.mark.asyncio
async def test_continue_session(temp_session_dir, bot_config):
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
            "num_messages": 2,
            "commands_run": 1,
            "status": "completed"
        }
        conversation = {
            "messages": [
                {"role": "system", "content": "You are a test assistant.", "timestamp": "2025-04-01T12:00:00"},
                {"role": "user", "content": "Hello", "timestamp": "2025-04-01T12:01:00"},
                {"role": "assistant", "content": "Hi there!", "timestamp": "2025-04-01T12:02:00"}
            ]
        }
        session_log = {"events": []}
        
        with open(prev_session_dir / "session.json", "w") as f:
            json.dump(session_info, f)
        with open(prev_session_dir / "conversation.json", "w") as f:
            json.dump(conversation, f)
        with open(prev_session_dir / "log.json", "w") as f:
            json.dump(session_log, f)
            
        # Mock the find_latest_session to return our previous session
        mock_find_latest.return_value = prev_session_dir
        
        # Create a new session with continue_session flag
        with patch("bots.session.BotLLM", MockBotLLM):
            session = Session(bot_config, temp_session_dir, continue_session=True)
            
            # Check that previous messages were loaded
            assert len(session.conversation.messages) == 3
            assert session.conversation.messages[0].role == MessageRole.SYSTEM
            assert session.conversation.messages[1].role == MessageRole.USER
            assert session.conversation.messages[1].content == "Hello"
            assert session.conversation.messages[2].role == MessageRole.ASSISTANT
            assert session.conversation.messages[2].content == "Hi there!"
            
            # Check that token usage was loaded
            assert session.session_info.token_usage.prompt_tokens == 100
            assert session.session_info.token_usage.completion_tokens == 50
            assert session.session_info.token_usage.total_tokens == 150
            
            # Check that status was reset to active
            assert session.session_info.status == SessionStatus.ACTIVE
            assert session.session_info.end_time is None


@pytest.mark.asyncio
async def test_add_message(temp_session_dir, bot_config):
    """Test adding messages to the session."""
    with patch("bots.session.BotLLM", MockBotLLM):
        session = Session(bot_config, temp_session_dir)

        # Add user message
        session.add_message(MessageRole.USER, "Hello, bot!")

        # Check if message was added
        assert len(session.conversation.messages) == 1
        assert session.conversation.messages[0].role == MessageRole.USER
        assert session.conversation.messages[0].content == "Hello, bot!"
        assert session.session_info.num_messages == 1

        # Add assistant message
        session.add_message(MessageRole.ASSISTANT, "Hello, user!")

        # Check if message was added
        assert len(session.conversation.messages) == 2
        assert session.conversation.messages[1].role == MessageRole.ASSISTANT
        assert session.conversation.messages[1].content == "Hello, user!"
        assert session.session_info.num_messages == 2


@pytest.mark.asyncio
async def test_execute_command(temp_session_dir, bot_config):
    """Test executing commands."""
    with patch("bots.session.BotLLM", MockBotLLM):
        session = Session(bot_config, temp_session_dir)

        # Execute a simple echo command
        response = await session.execute_command("echo 'test'")

        # Check response
        assert response.command == "echo 'test'"
        assert "test" in response.output
        assert response.exit_code == 0
        assert response.error is None

        # Check session state
        assert session.session_info.commands_run == 1


# Command validation and handling have been moved entirely to pydantic_tools.py
# These tests are being removed as part of architectural simplification


@pytest.mark.asyncio
async def test_interactive_session_start(temp_session_dir, bot_config):
    """Test the start of an interactive session."""
    with patch("bots.session.BotLLM", MockBotLLM):
        session = Session(bot_config, temp_session_dir)

        # Mock the console.print method to avoid output during test
        with patch("rich.console.Console.print"):
            # Mock the input function to simulate user exit
            with patch("builtins.input", side_effect=["/exit"]):
                await session.start_interactive()

        # Check if system message was added with context information
        assert len(session.conversation.messages) >= 1
        assert session.conversation.messages[0].role == MessageRole.SYSTEM
        assert "You are a test assistant." in session.conversation.messages[0].content
        assert "Environment Information" in session.conversation.messages[0].content


@pytest.mark.asyncio
async def test_handle_slash_command(temp_session_dir, bot_config):
    """Test handling slash commands."""
    with patch("bots.session.BotLLM", MockBotLLM):
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
    with patch("bots.session.BotLLM", MockBotLLM):
        session = Session(bot_config, temp_session_dir)
        context_info = session._get_context_info()

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
async def test_one_shot_session(temp_session_dir, bot_config):
    """Test one-shot session mode."""
    with patch("bots.session.BotLLM", MockBotLLM):
        session = Session(bot_config, temp_session_dir)

        # Set up mocks for print function
        with patch("builtins.print") as mock_print:
            await session.handle_one_shot("Hello, bot!")

        # Check if messages were added (system + user + assistant)
        assert len(session.conversation.messages) == 3
        assert session.conversation.messages[0].role == MessageRole.SYSTEM
        assert "You are a test assistant." in session.conversation.messages[0].content
        assert "Environment Information" in session.conversation.messages[0].content
        assert session.conversation.messages[1].role == MessageRole.USER
        assert session.conversation.messages[1].content == "Hello, bot!"
        assert session.conversation.messages[2].role == MessageRole.ASSISTANT

        # Check if response was printed
        mock_print.assert_any_call("This is a test response.")

        # Check session state
        assert session.session_info.end_time is not None
