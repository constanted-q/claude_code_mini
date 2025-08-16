"""
Agent class for handling LLM API interactions and text generation.
"""

import os
import time
from typing import Dict, Any, List
import yaml
from models import KimiModelClient


class Agent:
    def __init__(self, config_path: str = "config.yml"):
        """Initialize the Agent with configuration."""
        self.config = self._load_config(config_path)
        self.api_key = os.getenv("MOONSHOT_API_KEY", "mock-api-key")
        
        # Initialize model client if API key is available
        if self.api_key and self.api_key != "mock-api-key":
            try:
                self.model_client = KimiModelClient(self.config)
                self.use_real_model = True
            except Exception as e:
                print(f"[Agent] Failed to initialize model client: {e}")
                self.model_client = None
                self.use_real_model = False
        else:
            self.model_client = None
            self.use_real_model = False
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                # If file is empty or contains only whitespace, yaml.safe_load returns None
                if config is None:
                    return self._default_config()
                return config
        except FileNotFoundError:
            return self._default_config()
        except yaml.YAMLError as e:
            print(f"Error parsing config file: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration if file loading fails."""
        return {
            "model": "kimi-k2-0711-preview",
            "base_url": "https://api.moonshot.cn/v1",
            "max_tokens": 4096,
            "temperature": 0.2,
            "verbose": False
        }
    
    def generate_response(self, message: str, context: List[Dict[str, str]] = None, tool_schemas: List[Dict[str, Any]] = None) -> Any:
        """
        Generate a response to the user message using real LLM or fallback to mock.
        
        Args:
            message: User input message
            context: Optional conversation context
            tool_schemas: Optional tool schemas for function calling
            
        Returns:
            Generated response (string or dict with tool_calls)
        """


        if self.config.get("verbose", False):
            print(f"[Agent] Processing message: {message[:50]}...")
        
        # Use real model if available
        if self.use_real_model and self.model_client:
            try:
                return self.model_client.generate_response(message, context, tool_schemas)
            except Exception as e:
                print(f"[Agent] Model API failed, falling back to mock: {e}")
                # Fall through to mock response
        
        # Fallback mock responses (when no API key or API fails)
        return self._generate_mock_response(message, tool_schemas)
    
    def _generate_mock_response(self, message: str, tool_schemas: List[Dict[str, Any]] = None) -> Any:
        """Generate mock responses with potential tool usage."""
        if self.config.get("verbose", False):
            print(f"\n[Agent] Mock Response Generation:")
            print(f"  Input message: {message[:100]}{'...' if len(message) > 100 else ''}")
            print(f"  Available tools: {len(tool_schemas) if tool_schemas else 0}")
            if tool_schemas:
                tool_names = [schema["function"]["name"] for schema in tool_schemas]
                print(f"  Tool names: {tool_names}")
        
        time.sleep(0.1)  # Simulate API delay
        
        message_lower = message.lower()
        
        # Check if tools are available and message suggests tool usage
        if tool_schemas and self._should_use_tools_mock(message_lower):
            if self.config.get("verbose", False):
                print(f"  Decision: Generate tool response")
            return self._generate_mock_tool_response(message, tool_schemas)
        
        # Regular text responses
        if self.config.get("verbose", False):
            print(f"  Decision: Generate text response")
        
        if "hello" in message_lower or "hi" in message_lower:
            response = "Hello! I'm a Claude Code mini assistant. How can I help you today?"
        elif "how are you" in message_lower:
            response = "I'm doing well, thank you for asking! I'm ready to assist you with any questions or tasks."
        elif "what" in message_lower and ("can you do" in message_lower or "are you" in message_lower):
            tools_info = ""
            if tool_schemas:
                tool_names = [schema["function"]["name"] for schema in tool_schemas]
                tools_info = f" I have access to these tools: {', '.join(tool_names)}."
            response = f"I'm a simple chatbot implementation. Currently, I can have conversations with you.{tools_info} In the future, I'll be enhanced with more capabilities!"
        elif "bye" in message_lower or "goodbye" in message_lower:
            response = "Goodbye! It was nice chatting with you. Use /exit to end our conversation."
        elif "help" in message_lower:
            response = "I'm here to help! You can ask me questions, have a conversation, or type /exit to quit."
        else:
            # Generate a contextual response based on message length and content
            word_count = len(message.split())
            if word_count > 20:
                response = f"That's quite a detailed message! I understand you're saying something about '{message.split()[0]}'. Could you tell me more?"
            elif word_count > 5:
                response = f"Interesting point about '{message.split()[-1]}'. I'd like to hear your thoughts on this topic."
            else:
                response = f"I see you mentioned '{message}'. That's an interesting topic. What would you like to know more about?"
        
        if self.config.get("verbose", False):
            print(f"  Generated response: {response[:100]}{'...' if len(response) > 100 else ''}")
            print()
        
        return {"content": response}
    
    def _should_use_tools_mock(self, message_lower: str) -> bool:
        """Determine if mock response should include tool usage."""
        tool_triggers = [
            "read", "file", "open", "show me", "what's in", "content of",
            "look at", "examine", "check", "view", "display"
        ]
        return any(trigger in message_lower for trigger in tool_triggers)
    
    def _generate_mock_tool_response(self, message: str, tool_schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate mock response with tool calls."""
        message_lower = message.lower()
        
        if self.config.get("verbose", False):
            print(f"  Generating mock tool response for: {message_lower[:50]}...")
        
        # Find appropriate tool for mock usage
        read_tool = None
        for schema in tool_schemas:
            if schema["function"]["name"] == "read_file":
                read_tool = schema
                break
        
        if read_tool and ("read" in message_lower or "file" in message_lower):
            # Generate mock tool call for file reading
            import re
            
            if self.config.get("verbose", False):
                print(f"  Detected file reading request, generating read_file tool call")
            
            # Try to extract filename from message
            file_patterns = [
                r'["\']([\w\./\-_]+\.[\w]+)["\']',  # "filename.ext"
                r'\b([\w\-_]+\.py)\b',  # python files
                r'\b([\w\-_]+\.txt)\b',  # text files
                r'\b([\w\-_]+\.md)\b',   # markdown files
            ]
            
            filename = None
            for pattern in file_patterns:
                match = re.search(pattern, message)
                if match:
                    filename = match.group(1)
                    break
            
            if not filename:
                filename = "README.md"  # Default fallback
            
            if self.config.get("verbose", False):
                print(f"  Extracted filename: {filename}")
                print()
            
            return {
                "content": f"I'll read the {filename} file for you.",
                "tool_calls": [{
                    "id": "mock_call_1",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": {"file_path": filename}
                    }
                }]
            }
        
        # Fallback to regular response
        if self.config.get("verbose", False):
            print(f"  No specific tool pattern matched, using fallback response")
            print()
        
        return {"content": "I'd like to help you with that. Let me use the available tools to assist you."}
    
    def get_model_info(self) -> Dict[str, Any]:
        """Return information about the current model configuration."""
        if self.use_real_model and self.model_client:
            return self.model_client.get_model_info()
        else:
            return {
                "model": self.config.get("model", "unknown"),
                "max_tokens": self.config.get("max_tokens", 0),
                "temperature": self.config.get("temperature", 0.0),
                "has_api_key": bool(self.api_key and self.api_key != "mock-api-key"),
                "using_mock": True
            }