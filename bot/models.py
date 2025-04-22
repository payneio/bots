"""Data models for bot."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of message sender."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """Message in a conversation."""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class CommandExecution(BaseModel):
    """Record of a command execution."""

    command: str
    output: str
    exit_code: int
    timestamp: datetime = Field(default_factory=datetime.now)
    approved: bool = False


class TokenUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class SessionStatus(str, Enum):
    """Status of a session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"


class SessionInfo(BaseModel):
    """Session information."""

    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    model: str
    provider: str
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    num_messages: int = 0
    commands_run: int = 0
    status: SessionStatus = SessionStatus.ACTIVE


class SessionEvent(BaseModel):
    """Event in a session log."""

    event_type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Dict[str, Union[str, int, bool, None]] = Field(default_factory=dict)


class Conversation(BaseModel):
    """Conversation in a session."""

    messages: List[Message] = Field(default_factory=list)


class SessionLog(BaseModel):
    """Log of session events."""

    events: List[SessionEvent] = Field(default_factory=list)
