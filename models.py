"""
Model client for handling LLM API interactions using OpenAI SDK.
Supports Kimi K2 model through Moonshot API.
"""

import os
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI


class KimiModelClient:
    def __init__(self, config: Dict[str, Any]):
        """Initialize Kimi model client with configuration."""
        self.config = config
        self.api_key = os.getenv("MOONSHOT_API_KEY")
        
        if not self.api_key:
            raise ValueError("MOONSHOT_API_KEY environment variable is required")
        
        # Initialize OpenAI client with Moonshot base URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.config.get("base_url", "https://api.moonshot.cn/v1")
        )
        
        self.model = self.config.get("model", "kimi-k2-0711-preview")
        self.max_tokens = self.config.get("max_tokens", 4096)
        self.temperature = self.config.get("temperature", 0.2)
        
    def generate_response(self, message: str, context: List[Dict[str, str]] = None, tool_schemas: List[Dict[str, Any]] = None) -> Any:
        """
        Generate response using Kimi K2 model.
        
        Args:
            message: User input message
            context: Optional conversation context as list of message dicts
            tool_schemas: Optional tool schemas for function calling
            
        Returns:
            Generated response (string or dict with tool_calls)
            
        Raises:
            Exception: If API call fails
        """
        try:
            # Build messages for API call
            messages = self._build_messages(message, context)
            
            # Build API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }


            
            # Add tools if provided
            if tool_schemas:
                api_params["tools"] = tool_schemas
                
            # Verbose logging for request
            if self.config.get("verbose", False):
                print(f"\n[Model] LLM API Request:")
                print(f"  Model: {self.model}")
                print(f"  Messages: {len(messages)} messages")
                print(f"  Tools: {len(tool_schemas) if tool_schemas else 0} tools")
                print(f"  Temperature: {self.temperature}")
                print(f"  Max tokens: {self.max_tokens}")
                
                # Print formatted messages
                print(f"  Request messages:")
                for i, msg in enumerate(messages):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        content_preview = content[:100] + "..." if len(content) > 100 else content
                    else:
                        content_preview = f"[{type(content).__name__}] {str(content)[:100]}..."
                    print(f"    {i+1}. {role}: {content_preview}")
                    if "tool_calls" in msg:
                        print(f"       Tool calls: {len(msg['tool_calls'])}")
                
                if tool_schemas:
                    print(f"  Available tools: {[t['function']['name'] for t in tool_schemas]}")
                print()

            # Make API call
            response = self.client.chat.completions.create(**api_params)
            
            # Extract response
            message_response = response.choices[0].message
            
            # Verbose logging for response
            if self.config.get("verbose", False):
                print(f"[Model] LLM API Response:")
                print(f"  Role: {message_response.role}")
                if message_response.content:
                    content_preview = message_response.content[:200] + "..." if len(message_response.content) > 200 else message_response.content
                    print(f"  Content: {content_preview}")
                else:
                    print(f"  Content: None")
                
                if hasattr(message_response, 'tool_calls') and message_response.tool_calls:
                    print(f"  Tool calls: {len(message_response.tool_calls)}")
                    for i, call in enumerate(message_response.tool_calls):
                        print(f"    {i+1}. {call.function.name}({call.function.arguments[:100]}...)")
                else:
                    print(f"  Tool calls: None")
                
                # Usage information if available
                if hasattr(response, 'usage') and response.usage:
                    print(f"  Tokens - Prompt: {response.usage.prompt_tokens}, Completion: {response.usage.completion_tokens}, Total: {response.usage.total_tokens}")
                print()
            
            # Check if response has tool calls
            if hasattr(message_response, 'tool_calls') and message_response.tool_calls:
                formatted_response = self._format_tool_response(message_response)
                if self.config.get("verbose", False):
                    print(f"[Model] Formatted response with {len(formatted_response.get('tool_calls', []))} tool calls")
                return formatted_response
            else:
                # Regular text response - return in consistent format
                content = message_response.content.strip() if message_response.content else ""
                if self.config.get("verbose", False):
                    print(f"[Model] Formatted text response ({len(content)} chars)")
                return {"content": content}
            
        except Exception as e:
            error_msg = f"Error calling Kimi API: {str(e)}"
            print(f"[Model] {error_msg}")
            # Return a fallback response instead of raising
            return {"content": f"I apologize, but I'm having trouble connecting to the AI service right now. Error: {str(e)}"}
    
    def _format_tool_response(self, message_response) -> Dict[str, Any]:
        """Format a response containing tool calls."""
        import json
        
        result = {
            "content": message_response.content or "",
            "tool_calls": []
        }
        
        for tool_call in message_response.tool_calls:
            # Parse arguments (they come as JSON string)
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                # Fallback to raw string if JSON parsing fails
                arguments = {"raw_arguments": tool_call.function.arguments}
            
            formatted_call = {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": arguments
                }
            }
            result["tool_calls"].append(formatted_call)
        
        return result
    
    def _build_messages(self, message: str, context: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """
        Build messages array for API call from unified context format and current message.
        
        Args:
            message: Current user message
            context: Previous conversation context in unified format
            
        Returns:
            List of message dictionaries for API
        """
        messages = []
        
        # Add system message for context
        system_content = "You are a helpful AI assistant. Provide clear, concise, and helpful responses."
        
        # Add tool usage instructions if context contains tools
        if context and any(ctx.get("type") == "tool" for ctx in context):
            system_content += "\n\nWhen using tools, provide helpful explanations of what you're doing and interpret the results for the user."
        
        messages.append({
            "role": "system",
            "content": system_content
        })

        
        # Add context messages if available
        if context:
            for ctx_entry in context:
                if ctx_entry.get("type") == "conversation" and ctx_entry.get("role") in ["user", "assistant"]:
                    # Check if assistant message has tool calls
                    content = ctx_entry["content"]
                    metadata = ctx_entry.get("metadata", {})

                    message_dict = {
                        "role": ctx_entry["role"],
                        "content": content
                    }

                    if "tool_calls" in metadata:
                        formatted_tool_calls = []
                        for tool_call in metadata["tool_calls"]:
                            formatted_call = tool_call.copy()
                            if "function" in formatted_call and "arguments" in formatted_call["function"]:
                                args = formatted_call["function"]["arguments"]
                                # If arguments is a dict, convert to JSON string
                                if isinstance(args, dict):
                                    formatted_call["function"]["arguments"] = json.dumps(args)
                            formatted_tool_calls.append(formatted_call)

                        if formatted_tool_calls:
                            message_dict["tool_calls"] = formatted_tool_calls

                    messages.append(message_dict)

                elif ctx_entry.get("type") == "tool" and ctx_entry.get("role") == "tool":
                    # Handle tool results - format as OpenAI tool message
                    tool_metadata = ctx_entry.get("metadata", {})
                    tool_call_id = tool_metadata.get("tool_call_id")

                    print(f"###debug: tool_call_id {tool_call_id} in models 255")

                    # Skip tool results without valid tool_call_id to prevent API errors
                    if not tool_call_id or tool_call_id == "unknown":
                        if self.config.get("verbose", False):
                            print(f"[Model] Skipping tool result without tool_call_id: {tool_call_id}")
                        continue

                    # Format tool result as JSON
                    tool_result = {
                        "content": ctx_entry["content"],
                        "success": tool_metadata.get("success", True),
                        # "metadata": tool_metadata
                    }

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })

                elif ctx_entry.get("type") == "repo" and ctx_entry.get("role") == "system":
                    # Future implementation for repo context
                    messages.append({
                        "role": "system",
                        "content": f"Repository context: {ctx_entry['content']}"
                    })

        
        # Add current user message
        messages.append({
            "role": "user",
            "content": message
        })
        
        return messages
    
    def get_model_info(self) -> Dict[str, Any]:
        """Return information about current model configuration."""
        return {
            "model": self.model,
            "base_url": self.config.get("base_url", "https://api.moonshot.cn/v1"),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "has_api_key": bool(self.api_key)
        }