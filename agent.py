"""
Agent class for handling LLM API interactions and text generation.
"""

import os
import time
from typing import Dict, Any, List
import yaml


class Agent:
    def __init__(self, config_path: str = "config.yml"):
        """Initialize the Agent with configuration."""
        self.config = self._load_config(config_path)
        self.api_key = os.getenv("KIMI_API_KEY", "mock-api-key")
        
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
            "model": "gpt-4",
            "max_tokens": 4096,
            "temperature": 0.2,
            "verbose": False
        }
    
    def generate_response(self, message: str, context: List[Dict[str, str]] = None) -> str:
        """
        Generate a response to the user message.
        Currently mocked - will integrate real LLM API later.
        
        Args:
            message: User input message
            context: Optional conversation context
            
        Returns:
            Generated response string
        """
        if self.config.get("verbose", False):
            print(f"[Agent] Processing message: {message[:50]}...")
        
        # Mock response generation with slight delay to simulate API call
        time.sleep(0.1)
        
        # Simple mock responses based on keywords
        message_lower = message.lower()
        
        if "hello" in message_lower or "hi" in message_lower:
            return "Hello! I'm a Claude Code mini assistant. How can I help you today?"
        elif "how are you" in message_lower:
            return "I'm doing well, thank you for asking! I'm ready to assist you with any questions or tasks."
        elif "what" in message_lower and ("can you do" in message_lower or "are you" in message_lower):
            return "I'm a simple chatbot implementation. Currently, I can have conversations with you. In the future, I'll be enhanced with more capabilities!"
        elif "bye" in message_lower or "goodbye" in message_lower:
            return "Goodbye! It was nice chatting with you. Use /exit to end our conversation."
        elif "help" in message_lower:
            return "I'm here to help! You can ask me questions, have a conversation, or type /exit to quit."
        else:
            # Generate a contextual response based on message length and content
            word_count = len(message.split())
            if word_count > 20:
                return f"That's quite a detailed message! I understand you're saying something about '{message.split()[0]}'. Could you tell me more?"
            elif word_count > 5:
                return f"Interesting point about '{message.split()[-1]}'. I'd like to hear your thoughts on this topic."
            else:
                return f"I see you mentioned '{message}'. That's an interesting topic. What would you like to know more about?"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Return information about the current model configuration."""
        return {
            "model": self.config.get("model", "unknown"),
            "max_tokens": self.config.get("max_tokens", 0),
            "temperature": self.config.get("temperature", 0.0),
            "has_api_key": bool(self.api_key and self.api_key != "mock-api-key")
        }