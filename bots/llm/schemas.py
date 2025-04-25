"""Schema definitions for LLM integration."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CommandAction(str, Enum):
    """Action to take for a command."""

    EXECUTE = "execute"
    ASK = "ask"
    DENY = "deny"


class CommandRequest(BaseModel):
    """A command request from the LLM."""

    command: str = Field(..., description="The command to execute")
    reason: str = Field(..., description="The reason for executing this command")


class CommandResponse(BaseModel):
    """A response to a command execution."""

    command: str = Field(..., description="The command that was executed")
    output: str = Field(..., description="The output of the command")
    exit_code: int = Field(..., description="The exit code of the command")
    error: Optional[str] = Field(None, description="Error message if the command failed")


class BotResponse(BaseModel):
    """A response from the bot."""

    message: str = Field(..., description="The message to display to the user")
    commands: List[CommandRequest] = Field(default_factory=lambda: [], description="Commands to execute")


class BotRequest(BaseModel):
    """A request to the bot."""

    message: str = Field(..., description="The user's message")
    context: Optional[str] = Field(None, description="Additional context for the bot")
