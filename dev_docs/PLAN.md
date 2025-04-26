# Implementing Pydantic AI Message History Best Practices

## Current Implementation Issues

Our current implementation has several issues compared to Pydantic AI best practices:

1. **Custom Message Format**: We use our own custom `Message` class with `MessageRole` enum instead of using Pydantic AI's native message format.

2. **String-Based Communication**: We convert our messages to a flat string-based prompt format, losing the structured nature of the conversation.

3. **Lack of Message History Parameter**: We don't use Pydantic AI's built-in `message_history` parameter for maintaining conversation context across runs.

4. **Missing Message Access Methods**: We don't leverage methods like `all_messages()` and `new_messages()` for accessing message history.

5. **Custom Serialization**: We implement our own serialization instead of using Pydantic AI's `ModelMessagesTypeAdapter` for saving and loading messages.

## Switching to Pydantic AI's Native Message Format

After analyzing our current implementation and Pydantic AI's message functionality, **we should replace our custom Message class with Pydantic AI's native message format** rather than maintaining both. This approach offers several advantages:

1. **Direct Integration**: Using Pydantic AI's message format directly eliminates the need for conversion logic.

2. **Future Compatibility**: We'll automatically benefit from future updates to Pydantic AI's message implementation.

3. **Standardization**: Following the standard approach makes our code easier to understand for developers familiar with Pydantic AI.

4. **Reduced Complexity**: One less custom model to maintain and synchronize.

## Implementation Plan

### Phase 1: Replace Our Message Class with Pydantic AI's Format

1. **Update Message Imports**:
   - Replace imports of our custom `Message` and `MessageRole` with Pydantic AI equivalents
   - Update type annotations throughout the codebase

```python
# Before
from bots.models import Message, MessageRole

# After
from pydantic_ai import Message
from pydantic_ai.message import Role as MessageRole
```

2. **Update Message Creation**:
   - Update code that creates Message instances to use Pydantic AI's format
   - Ensure compatibility with existing logic

```python
# Before
Message(role=MessageRole.USER, content="Hello")

# After
Message(role="user", content="Hello")  # Using string literals for roles
```

### Phase 2: Update Agent Execution

1. **Modify `generate` Method**:
   - Use the message history parameter in Agent.run() instead of constructing a prompt string
   - Maintain conversation continuity across runs

```python
async def generate(self, messages: List[pydantic_ai.Message], output_type: Type[T]) -> Any:
    """Generate a response using message history."""
    # Use messages directly as Pydantic AI message history
    
    # Create agent with the right output type
    agent = Agent(
        model=f"openai:{self.model_name}",
        output_type=output_type,
        temperature=self.temperature,
    )
    
    # Add command execution tool
    @agent.tool
    async def execute_command(ctx, command):
        # (tool implementation)
        pass
    
    # Run with message history instead of prompt string
    # Empty message with message history means "continue the conversation"
    result = await agent.run(message="", message_history=messages)
    
    return result.output
```

### Phase 3: Session and Conversation Updates

1. **Update Conversation Storage**:
   - Replace our custom Conversation class with Pydantic AI's message format
   - Update saving/loading logic to use Pydantic AI's serialization methods

```python
# Before
self.conversation = Conversation()  # Custom container with list of our Message objects

# After 
self.messages = []  # Direct list of Pydantic AI Message objects
```

2. **Update Serialization**:
   - Use Pydantic AI's ModelMessagesTypeAdapter for serialization

```python
# Save messages
def _save_messages(self) -> None:
    """Save messages to disk using Pydantic AI serialization."""
    messages_path = self.session_path / "messages.json"
    serialized = pydantic_ai.ModelMessagesTypeAdapter.serialize_json(self.messages)
    with open(messages_path, "w") as f:
        f.write(serialized)

# Load messages
def _load_messages(self, path: Path) -> List[pydantic_ai.Message]:
    """Load messages from disk using Pydantic AI deserialization."""
    with open(path, "r") as f:
        serialized = f.read()
    return pydantic_ai.ModelMessagesTypeAdapter.deserialize_json(serialized)
```

3. **Update Interactive and One-Shot Modes**:
   - Modify the interactive session to leverage message history continuity
   - Update the one-shot session to support message history when needed

### Phase 4: Testing Updates

1. **Update Test Mocks**:
   - Create proper mocks for the Pydantic AI message functionality
   - Update existing tests to work with the new message structure
   - Add new tests for message history continuity

2. **Fix Regression Tests**:
   - Ensure all existing tests pass with the new implementation
   - Fix any breaking changes to maintain API compatibility

## API Changes

### Current API:
```python
async def generate_response(self, messages: List[Message], context: Optional[str] = None) -> Tuple[BotResponse, TokenUsage]:
    """Generate a response from the LLM."""
    # Converts messages to string prompt
    prompt = self._messages_to_prompt(messages)
    # ...
```

### New API:
```python
async def generate_response(self, messages: List[pydantic_ai.Message], context: Optional[str] = None) -> Tuple[BotResponse, TokenUsage]:
    """Generate a response from the LLM."""
    # Use messages directly as Pydantic AI message history
    result = await agent.run(message="", message_history=messages)
    # ...
```

## Implementation Strategy

1. **Phased Rollout**:
   - Implement changes in stages to maintain stability
   - Start with replacing the Message class with Pydantic AI's format
   - Update agent execution to use message_history
   - Update session management and serialization

2. **Migration Path**:
   - Create migration utilities for existing serialized conversations
   - Test with both legacy and new message formats
   - Provide clear documentation for any API changes

3. **Testing Focus**:
   - Add comprehensive tests for each phase
   - Test message continuity across multiple interactions
   - Verify serialization/deserialization works correctly
   - Ensure backward compatibility with existing code

## Benefits of This Approach

1. **Simpler Codebase**: Directly using Pydantic AI messages reduces conversion overhead and complexity

2. **Better Alignment**: Our implementation will be more aligned with Pydantic AI's recommended patterns

3. **Improved Functionality**: We gain access to built-in functionality like message history continuity and serialization

4. **Future-Proof**: As Pydantic AI evolves, we automatically get improvements without additional work

## Timeline

1. **Phase 1 (Replace Message Class)**: 1-2 days
2. **Phase 2 (Update Agent Execution)**: 2-3 days
3. **Phase 3 (Session/Conversation Updates)**: 2-3 days
4. **Phase 4 (Testing)**: 2-3 days

Total: 7-11 days for full implementation