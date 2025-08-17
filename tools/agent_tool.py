"""
Agent Tool implementation for exposing sub-agents as tools to the main agent.
This allows the main CLI agent to spawn and coordinate sub-agents.
"""

import time
from typing import Dict, Any, Optional
from .base_tool import Tool, ToolExecutionResult


class AgentTool(Tool):
    """
    Tool wrapper that exposes a SubAgent as a callable tool.
    Allows the main agent to delegate tasks to specialized sub-agents.
    """
    
    def __init__(self, sub_agent):
        """
        Initialize AgentTool with a SubAgent instance.
        
        Args:
            sub_agent: SubAgent instance to wrap
        """
        super().__init__()
        self.sub_agent = sub_agent
        self._tool_name = f"agent_{self.sub_agent.name}"
    
    @classmethod
    def get_name(cls) -> str:
        """Get the tool name. This will be overridden by instance method."""
        return "agent_tool"
    
    def get_name(self) -> str:
        """Get the tool name for this specific sub-agent."""
        return self._tool_name
    
    @classmethod
    def get_description(cls) -> str:
        """Get the tool description. This will be overridden by instance method."""
        return "Sub-agent tool for specialized task handling"
    
    def get_description(self) -> str:
        """Get the description for this specific sub-agent."""
        return f"Sub-agent '{self.sub_agent.name}': {self.sub_agent.description}"
    
    @classmethod
    def get_instructions(cls) -> str:
        """Get instructions. This will be overridden by instance method."""
        return "Use this tool to delegate tasks to specialized sub-agents"
    
    def get_instructions(self) -> str:
        """Get instructions for this specific sub-agent."""
        base_instructions = f"Use this sub-agent for: {self.sub_agent.description}"
        if self.sub_agent.instructions:
            base_instructions += f"\n\nSpecific instructions: {self.sub_agent.instructions}"
        
        available_tools = ", ".join(self.sub_agent.available_tools)
        base_instructions += f"\n\nAvailable tools: {available_tools}"
        
        return base_instructions
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Get the input schema. This will be overridden by instance method."""
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Task description for the sub-agent"
                }
            },
            "required": ["prompt"]
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get the input schema for this specific sub-agent."""
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": f"Task description for {self.sub_agent.name} sub-agent. {self.sub_agent.description}"
                },
                "max_iterations": {
                    "type": "integer",
                    "description": "Maximum number of iterations (optional, default from config)",
                    "minimum": 1,
                    "maximum": 20
                }
            },
            "required": ["prompt"]
        }
    
    def execute(self, tool_context=None, **kwargs) -> ToolExecutionResult:
        """
        Execute the sub-agent with the given prompt.
        
        Args:
            tool_context: Shared tool context (passed to sub-agent)
            prompt: Task description for the sub-agent
            max_iterations: Optional override for max iterations
            
        Returns:
            ToolExecutionResult with sub-agent output
        """
        prompt = kwargs.get("prompt", "")
        max_iterations = kwargs.get("max_iterations")
        
        if not prompt.strip():
            return ToolExecutionResult(
                content="",
                success=False,
                error="Empty prompt provided to sub-agent",
                metadata={"agent_name": self.sub_agent.name}
            )
        
        try:
            # Override max_iterations if provided
            original_max_iterations = None
            if max_iterations is not None:
                original_max_iterations = self.sub_agent.max_iterations
                self.sub_agent.max_iterations = max_iterations
            
            start_time = time.time()
            
            # Set the tool context for the sub-agent
            self.sub_agent.tool_context = tool_context
            
            # Execute the sub-agent
            result = self.sub_agent.execute(prompt, **kwargs)
            
            execution_time = time.time() - start_time
            
            # Restore original max_iterations if it was overridden
            if original_max_iterations is not None:
                self.sub_agent.max_iterations = original_max_iterations
            
            if result.get("success", False):
                # Format successful result
                agent_result = result.get("result", "")
                metadata = result.get("metadata", {})
                metadata.update({
                    "tool_execution_time": execution_time,
                    "sub_agent_tool": self.get_name()
                })
                
                # Create a formatted response
                formatted_content = f"Sub-agent '{self.sub_agent.name}' completed the task:\n\n{agent_result}"
                
                if metadata.get("iterations", 0) > 1:
                    formatted_content += f"\n\n(Completed in {metadata.get('iterations')} iterations)"
                
                return ToolExecutionResult(
                    content=formatted_content,
                    success=True,
                    metadata=metadata
                )
            else:
                # Handle sub-agent failure
                error_msg = result.get("error", "Sub-agent execution failed")
                metadata = result.get("metadata", {})
                metadata.update({
                    "tool_execution_time": execution_time,
                    "sub_agent_tool": self.get_name()
                })
                
                return ToolExecutionResult(
                    content=f"Sub-agent '{self.sub_agent.name}' failed: {error_msg}",
                    success=False,
                    error=error_msg,
                    metadata=metadata
                )
                
        except Exception as e:
            return ToolExecutionResult(
                content="",
                success=False,
                error=f"Error executing sub-agent '{self.sub_agent.name}': {str(e)}",
                metadata={
                    "agent_name": self.sub_agent.name,
                    "exception_type": type(e).__name__
                }
            )
    
    def get_sub_agent_info(self) -> Dict[str, Any]:
        """Get information about the wrapped sub-agent."""
        return self.sub_agent.get_info()
    
    def to_openai_function(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function calling format.
        Override to use instance-specific information.
        """
        return {
            "type": "function",
            "function": {
                "name": self.get_name(),
                "description": self.get_description(),
                "parameters": self.get_input_schema()
            }
        }


def create_agent_tool_from_config(config_path: str, tool_context=None) -> Optional[AgentTool]:
    """
    Create an AgentTool from a sub-agent configuration file.
    
    Args:
        config_path: Path to the sub-agent YAML config file
        tool_context: Shared tool context
        
    Returns:
        AgentTool instance or None if creation fails
    """
    try:
        from sub_agent import SubAgent
        
        sub_agent = SubAgent(config_path, tool_context)
        agent_tool = AgentTool(sub_agent)
        
        return agent_tool
        
    except Exception as e:
        print(f"[AgentTool] Failed to create agent tool from {config_path}: {e}")
        return None