"""
Model client for handling LLM API interactions using OpenAI SDK.
Supports Kimi K2 model through Moonshot API.
"""

import os
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
        
    def generate_response(self, message: str, context: List[Dict[str, str]] = None) -> str:
        """
        Generate response using Kimi K2 model.
        
        Args:
            message: User input message
            context: Optional conversation context as list of message dicts
            
        Returns:
            Generated response string
            
        Raises:
            Exception: If API call fails
        """
        try:
            # Build messages for API call
            messages = self._build_messages(message, context)
            print(messages)
            
            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Extract and return response content
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            error_msg = f"Error calling Kimi API: {str(e)}"
            print(f"[Model] {error_msg}")
            # Return a fallback response instead of raising
            return f"I apologize, but I'm having trouble connecting to the AI service right now. Error: {str(e)}"
    
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
        messages.append({
            "role": "system",
            "content": "You are a helpful AI assistant. Provide clear, concise, and helpful responses."
        })
        
        # Add context messages if available
        if context:
            for ctx_entry in context:
                # Handle unified context format
                if ctx_entry.get("type") == "conversation" and ctx_entry.get("role") in ["user", "assistant"]:
                    messages.append({
                        "role": ctx_entry["role"],
                        "content": ctx_entry["content"]
                    })
                # Future: Handle other context types (repo, tool, etc.)
                elif ctx_entry.get("type") == "repo" and ctx_entry.get("role") == "system":
                    # Future implementation for repo context
                    messages.append({
                        "role": "system", 
                        "content": f"Repository context: {ctx_entry['content']}"
                    })
                elif ctx_entry.get("type") == "tool" and ctx_entry.get("role") == "tool":
                    # Future implementation for tool context
                    messages.append({
                        "role": "system",
                        "content": f"Tool result: {ctx_entry['content']}"
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