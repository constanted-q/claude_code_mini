"""
Base tool class for implementing tools in the CLI agent.
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class ToolExecutionResult:
    """Result of tool execution with metadata."""
    
    def __init__(self, content: str, success: bool = True, error: Optional[str] = None, 
                 metadata: Optional[Dict[str, Any]] = None):
        self.content = content
        self.success = success
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "content": self.content,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class Tool(ABC):
    """Abstract base class for all tools."""
    
    def __init__(self):
        """Initialize the tool."""
        pass
    
    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Get the tool name."""
        pass
    
    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        """Get the tool description."""
        pass
    
    @classmethod
    @abstractmethod
    def get_instructions(cls) -> str:
        """Get instructions for using this tool."""
        pass
    
    @classmethod
    @abstractmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Get the JSON schema for tool input parameters."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolExecutionResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool parameters based on input schema
            
        Returns:
            ToolExecutionResult with content and metadata
        """
        pass
    
    def validate_input(self, **kwargs) -> bool:
        """
        Validate input parameters against the schema.
        
        Args:
            **kwargs: Input parameters to validate
            
        Returns:
            True if valid, raises ValueError if invalid
        """
        schema = self.get_input_schema()
        required_params = schema.get("required", [])
        properties = schema.get("properties", {})
        
        # Check required parameters
        for param in required_params:
            if param not in kwargs:
                raise ValueError(f"Missing required parameter: {param}")
        
        # Check parameter types (basic validation)
        for param, value in kwargs.items():
            if param in properties:
                expected_type = properties[param].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    raise ValueError(f"Parameter {param} must be a string")
                elif expected_type == "integer" and not isinstance(value, int):
                    raise ValueError(f"Parameter {param} must be an integer")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    raise ValueError(f"Parameter {param} must be a boolean")
        
        return True
    
    def post_process(self, result: ToolExecutionResult) -> ToolExecutionResult:
        """
        Post-process tool execution result.
        
        Args:
            result: Raw tool execution result
            
        Returns:
            Processed result
        """
        # Default implementation - can be overridden by subclasses
        return result
    
    def safe_execute(self, **kwargs) -> ToolExecutionResult:
        """
        Safely execute the tool with error handling.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            ToolExecutionResult (success=False if error occurred)
        """
        try:
            # Validate input
            self.validate_input(**kwargs)
            
            # Execute tool
            result = self.execute(**kwargs)
            
            # Post-process result
            processed_result = self.post_process(result)
            
            return processed_result
            
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            return ToolExecutionResult(
                content="",
                success=False,
                error=error_msg,
                metadata={"exception_type": type(e).__name__}
            )
    
    def to_openai_function(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function calling format.
        
        Returns:
            OpenAI function schema dictionary
        """
        return {
            "type": "function",
            "function": {
                "name": self.get_name(),
                "description": self.get_description(),
                "parameters": self.get_input_schema()
            }
        }
    
    def to_unified_context(self, result: ToolExecutionResult, tool_call_id: str = None) -> Dict[str, Any]:
        """
        Convert tool result to unified context format.
        
        Args:
            result: Tool execution result
            tool_call_id: Optional tool call ID for tracking
            
        Returns:
            Unified context entry
        """
        metadata = {
            "tool_name": self.get_name(),
            "execution_time": result.timestamp,
            "success": result.success,
            **result.metadata
        }
        
        if tool_call_id:
            metadata["tool_call_id"] = tool_call_id
        
        if result.error:
            metadata["error"] = result.error
        
        return {
            "type": "tool",
            "role": "tool",
            "content": result.content,
            "metadata": metadata
        }
    
    def get_help_text(self) -> str:
        """
        Get formatted help text for the tool.
        
        Returns:
            Formatted help string
        """
        schema = self.get_input_schema()
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        help_text = f"Tool: {self.get_name()}\n"
        help_text += f"Description: {self.get_description()}\n"
        help_text += f"Instructions: {self.get_instructions()}\n\n"
        help_text += "Parameters:\n"
        
        for param_name, param_info in properties.items():
            param_type = param_info.get("type", "unknown")
            param_desc = param_info.get("description", "No description")
            required_str = " (required)" if param_name in required else " (optional)"
            help_text += f"  - {param_name} ({param_type}){required_str}: {param_desc}\n"
        
        return help_text