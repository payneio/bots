"""Direct OpenAI integration for structured output."""

import json
import sys
from typing import Any, Dict, List, Optional, Tuple

import openai

from bot.config import BotConfig
from bot.llm.schemas import BotResponse, CommandRequest
from bot.models import Message, MessageRole, TokenUsage


def _convert_message_role(role: MessageRole) -> str:
    """Convert bot message role to OpenAI message role string.
    
    Args:
        role: The bot message role
        
    Returns:
        The OpenAI message role string
    """
    if role == MessageRole.USER:
        return "user"
    elif role == MessageRole.ASSISTANT:
        return "assistant"
    elif role == MessageRole.SYSTEM:
        return "system"
    else:
        return "user"


def _create_openai_client(api_key: str) -> openai.OpenAI:
    """Create an OpenAI client.
    
    Args:
        api_key: The API key to use
        
    Returns:
        The OpenAI client
    """
    return openai.OpenAI(api_key=api_key)


def _convert_messages_to_openai_format(messages: List[Message]) -> List[Dict[str, str]]:
    """Convert bot messages to OpenAI format.
    
    Args:
        messages: The bot messages
        
    Returns:
        The OpenAI formatted messages
    """
    return [
        {"role": _convert_message_role(msg.role), "content": msg.content}
        for msg in messages
    ]


def _get_bot_response_function() -> Dict[str, Any]:
    """Get the function definition for structured bot responses.
    
    Returns:
        The function definition
    """
    return {
        "name": "create_bot_response",
        "description": "Creates a response from the bot to the user",
        "parameters": {
            "type": "object",
            "properties": {
                "reply": {
                    "type": "string",
                    "description": "Your detailed response to the user"
                },
                "commands": {
                    "type": "array",
                    "description": "List of commands to execute",
                    "items": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "A shell command to run"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Explanation of why this command is being run"
                            }
                        },
                        "required": ["command", "reason"]
                    }
                }
            },
            "required": ["reply"]
        }
    }


async def generate_openai_response(
    config: BotConfig,
    messages: List[Message],
    context: Optional[str] = None,
) -> Tuple[BotResponse, TokenUsage]:
    """Generate a response using the OpenAI API directly.
    
    Args:
        config: The bot configuration
        messages: The conversation history
        context: Optional additional context
        
    Returns:
        The bot response and token usage
    """
    api_key = config.resolve_api_key()
    if not api_key:
        # Create a placeholder response
        response_text = (
            "Error: No API key available. Please set the API key in your configuration "
            "or environment variables."
        )
        return BotResponse(message=response_text, commands=[]), TokenUsage()
    
    # Create OpenAI client
    client = _create_openai_client(api_key)
    
    # Convert messages to OpenAI format
    openai_messages = _convert_messages_to_openai_format(messages)
    
    # Add context if provided
    if context:
        # Find the last user message
        for i in reversed(range(len(openai_messages))):
            if openai_messages[i]["role"] == "user":
                openai_messages[i]["content"] += f"\n\nContext: {context}"
                break
    
    functions = [_get_bot_response_function()]
    
    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model=config.model_name,
            messages=openai_messages,
            functions=functions,
            function_call={"name": "create_bot_response"},
            temperature=config.temperature,
        )
        
        # Extract response
        function_call = response.choices[0].message.function_call
        if function_call and function_call.arguments:
            try:
                function_args = json.loads(function_call.arguments)
                
                # Extract the reply and commands
                reply = function_args.get("reply", "Sorry, I couldn't generate a proper response.")
                raw_commands = function_args.get("commands", [])
                
                # Convert commands
                commands = [
                    CommandRequest(command=cmd["command"], reason=cmd["reason"])
                    for cmd in raw_commands
                    if "command" in cmd and "reason" in cmd
                ]
                
                # Create bot response
                bot_response = BotResponse(message=reply, commands=commands)
                
                # Extract token usage
                token_usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )
                
                return bot_response, token_usage
                
            except (json.JSONDecodeError, KeyError) as e:
                # Handle JSON errors
                print(f"Error parsing function arguments: {e}", file=sys.stderr)
                error_message = f"Error parsing function arguments: {e}"
                return BotResponse(message=error_message, commands=[]), TokenUsage()
        else:
            # Handle missing function call
            simple_response = response.choices[0].message.content or "No response generated"
            return BotResponse(message=simple_response, commands=[]), TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
    
    except openai.RateLimitError:
        error_message = "OpenAI API rate limit exceeded. Please try again later."
        return BotResponse(message=error_message, commands=[]), TokenUsage()
    
    except openai.AuthenticationError:
        error_message = "OpenAI API authentication error. Please check your API key."
        return BotResponse(message=error_message, commands=[]), TokenUsage()
    
    except (openai.APIError, openai.APIConnectionError) as e:
        error_message = f"OpenAI API error: {str(e)}"
        return BotResponse(message=error_message, commands=[]), TokenUsage()
    
    except Exception as e:
        # Handle other errors
        print(f"Error generating response: {e}", file=sys.stderr)
        error_message = f"Error generating response: {str(e)}"
        return BotResponse(message=error_message, commands=[]), TokenUsage()