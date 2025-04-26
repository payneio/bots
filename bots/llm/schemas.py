"""Schema definitions for LLM integration."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CommandAction(str, Enum):
    """Action to take for a command."""

    EXECUTE = "execute"
    ASK = "ask"
    DENY = "deny"


class CommandResponse(BaseModel):
    """A response to a command execution."""

    command: str = Field(..., description="The command that was executed")
    output: str = Field(..., description="The output of the command")
    exit_code: int = Field(..., description="The exit code of the command")
    error: Optional[str] = Field(None, description="Error message if the command failed")


class BotResponse(BaseModel):
    """A response from the bot."""

    message: str = Field(..., description="The message to display to the user")
