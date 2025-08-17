"""
Sub-agent implementation for hierarchical task decomposition.
Allows the main CLI agent to spawn specialized sub-agents for dedicated task handling.
"""

import os
import json
import yaml
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from models import KimiModelClient
from tools import get_tool, get_registry


class SubAgent:
    """
    A specialized agent that can be spawned by the main agent for dedicated task handling.
    Each sub-agent maintains its own context and can use a subset of available tools.
    """
    
    def __init__(self, config_path: str, tool_context=None):
        """
        Initialize sub-agent with configuration file.
        
        Args:
            config_path: Path to the sub-agent YAML configuration file
            tool_context: Shared tool context for file state consistency
        """
        self.config_path = config_path
        self.tool_context = tool_context
        self.context_history: List[Dict[str, Any]] = []
        self.max_context_length = 20  # Limit context to prevent overflow
        
        # Load configuration
        self.config = self._load_config(config_path)
        self.name = self.config.get("name", "unknown_agent")
        self.description = self.config.get("description", "")
        self.system_prompt = self.config.get("system_prompt", "You are a helpful AI assistant.")
        self.instructions = self.config.get("instructions", "")
        self.available_tools = self.config.get("available_tools", [])
        self.max_tokens = self.config.get("max_tokens", 2000)
        self.temperature = self.config.get("temperature", 0.3)
        self.max_iterations = self.config.get("max_iterations", 10)
        self.tool_schemas = self._get_available_tool_schemas()
        
        # Initialize model client
        self._initialize_model_client()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load sub-agent configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                if config is None:
                    raise ValueError("Empty configuration file")
                return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Sub-agent config file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")
    
    def _initialize_model_client(self):
        """Initialize model client with sub-agent specific settings."""
        # Use main config but override with sub-agent specific settings
        model_config = {
            "model": "kimi-k2-0711-preview",
            "base_url": "https://api.moonshot.cn/v1",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "verbose": False  # Sub-agents run quietly unless debugging
        }
        
        api_key = os.getenv("MOONSHOT_API_KEY")
        if api_key and api_key != "mock-api-key":
            try:
                self.model_client = KimiModelClient(model_config)
                self.use_real_model = True
            except Exception as e:
                print(f"[SubAgent {self.name}] Failed to initialize model client: {e}")
                self.model_client = None
                self.use_real_model = False
        else:
            self.model_client = None
            self.use_real_model = False
    
    def execute(self, task_prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Execute the sub-agent task with the given prompt.
        
        Args:
            task_prompt: The task description for the sub-agent
            **kwargs: Additional parameters
            
        Returns:
            Dict containing result, metadata, and execution info
        """
        start_time = time.time()
        iteration_count = 0
        
        # Initialize context with system message and task
        self._initialize_context(task_prompt)
        
        try:
            if self.tool_context:
                print(f"[SubAgent {self.name}] Starting execution with task: {task_prompt[:300]}...")
            
            # Main execution loop
            while iteration_count < self.max_iterations:
                iteration_count += 1
                
                # Get tool schemas for available tools
                tool_schemas = self.tool_schemas
                
                # Generate response from model
                if self.use_real_model and self.model_client:
                    response_data = self.model_client.generate_response(
                        task_prompt if iteration_count == 1 else "Continue based on the tool results above.",
                        self.context_history,
                        tool_schemas
                    )
                else:
                    # Mock response for testing
                    response_data = self._generate_mock_response(task_prompt, tool_schemas)
                
                # Handle response
                if "tool_calls" in response_data and response_data["tool_calls"]:
                    # Execute tool calls and continue
                    assistant_message = response_data.get("content", "")
                    print(f"sub-agent assistant message: {assistant_message}")
                    if assistant_message:
                        self._add_context("assistant", assistant_message, response_data.get("tool_calls"))
                    
                    tool_results = self._execute_tool_calls(response_data["tool_calls"])
                    
                    # Check if we should continue or if tools provided final answer
                    if any(result.get("final", False) for result in tool_results):
                        break
                        
                else:
                    # Final text response - we're done
                    final_response = response_data.get("content", "")
                    if final_response:
                        self._add_context("assistant", final_response)
                    break
            
            # Format final result
            result = self._format_result()
            
            execution_time = time.time() - start_time
            return {
                "success": True,
                "result": result,
                "metadata": {
                    "agent_name": self.name,
                    "execution_time": execution_time,
                    "iterations": iteration_count,
                    "context_length": len(self.context_history)
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "agent_name": self.name,
                    "execution_time": execution_time,
                    "iterations": iteration_count,
                    "context_length": len(self.context_history)
                }
            }
    
    def _initialize_context(self, task_prompt: str):
        """Initialize the sub-agent context with system prompt and task."""
        self.context_history = []
        
        # Add system message
        self._add_context("system", self.system_prompt)
        
        # Add initial user task
        self._add_context("user", task_prompt)
    
    def _add_context(self, role: str, content: str, tool_calls: List[Dict[str, Any]] = None):
        """Add a message to the context history."""
        timestamp = datetime.now().isoformat()
        message_id = len(self.context_history) + 1
        
        context_entry = {
            "type": "conversation",
            "role": role,
            "content": content,
            "metadata": {
                "timestamp": timestamp,
                "message_id": f"{message_id}_{role}",
                "agent": self.name
            }
        }
        
        if tool_calls:
            context_entry["metadata"]["tool_calls"] = tool_calls
        
        self.context_history.append(context_entry)
        
        # Manage context length
        if len(self.context_history) > self.max_context_length:
            # Keep system message and recent messages
            system_msg = self.context_history[0] if self.context_history[0].get("role") == "system" else None
            recent_messages = self.context_history[-(self.max_context_length-1):]
            
            self.context_history = ([system_msg] if system_msg else []) + recent_messages
    
    def _get_available_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI function schemas for available tools."""
        schemas = []
        registry = get_registry()
        if not registry.auto_registered:
            registry.auto_discover_tools()
        
        for tool_name in self.available_tools:
            try:
                tool_instance = registry.get_tool(tool_name)
                schemas.append(tool_instance.to_openai_function())
            except Exception as e:
                print(f"[SubAgent {self.name}] Warning: Tool {tool_name} not available: {e}")
        
        return schemas
    
    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tool calls and add results to context."""
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            tool_args = tool_call.get("function", {}).get("arguments", {})
            call_id = tool_call.get("id", "")
            
            try:
                # Check if tool is allowed
                if tool_name not in self.available_tools:
                    error_msg = f"Tool {tool_name} not available to sub-agent {self.name}"
                    result = {"success": False, "error": error_msg}
                else:
                    # Get and execute tool
                    tool = get_tool(tool_name)
                    execution_result = tool.safe_execute(tool_context=self.tool_context, **tool_args)
                    
                    result = {
                        "success": execution_result.success,
                        "content": execution_result.content,
                        "error": execution_result.error
                    }
                
                # Add tool result to context
                tool_context = {
                    "type": "tool",
                    "role": "tool",
                    "content": result.get("content", ""),
                    "metadata": {
                        "tool_name": tool_name,
                        "tool_call_id": call_id,
                        "success": result["success"],
                        "agent": self.name
                    }
                }
                
                if result.get("error"):
                    tool_context["metadata"]["error"] = result["error"]
                
                self.context_history.append(tool_context)
                results.append(result)
                
            except Exception as e:
                error_msg = f"Error executing tool {tool_name}: {e}"
                error_result = {"success": False, "error": error_msg}
                
                # Add error to context
                error_context = {
                    "type": "tool",
                    "role": "tool",
                    "content": f"Error: {error_msg}",
                    "metadata": {
                        "tool_name": tool_name,
                        "tool_call_id": call_id,
                        "success": False,
                        "error": error_msg,
                        "agent": self.name
                    }
                }
                self.context_history.append(error_context)
                results.append(error_result)
        
        return results
    
    def _format_result(self) -> str:
        """Format the final result from the context history."""
        # Get the last assistant message as the result
        for entry in reversed(self.context_history):
            if entry.get("role") == "assistant" and entry.get("content"):
                return entry["content"]
        
        return "Sub-agent completed execution but provided no final response."
    
    def _generate_mock_response(self, task_prompt: str, tool_schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate mock response for testing when no real model is available."""
        time.sleep(0.1)  # Simulate processing
        
        # Simple mock logic - if tools available and task mentions files, use read tool
        if tool_schemas and ("file" in task_prompt.lower() or "read" in task_prompt.lower()):
            return {
                "content": f"I'll help you with that task using the available tools.",
                "tool_calls": [{
                    "id": "mock_call_1",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": {"file_path": "README.md"}
                    }
                }]
            }
        
        return {
            "content": f"As sub-agent '{self.name}', I've completed the task: {task_prompt}. This is a mock response since no real model is configured."
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about this sub-agent."""
        return {
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "available_tools": self.available_tools,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "config_path": self.config_path
        }


def create_sub_agent(description: str, agent_name: str = None, save_config: bool = True) -> Dict[str, Any]:
    """
    Create a new sub-agent based on a description.
    Uses LLM to generate configuration and creates the SubAgent instance.
    
    Args:
        description: One-line description of what the sub-agent should do
        agent_name: Optional name for the agent (auto-generated if not provided)
        save_config: Whether to save the config to file
        
    Returns:
        Dict containing SubAgent instance and AgentTool instance
    """
    # Generate agent name if not provided
    if not agent_name:
        # Simple name generation from description
        words = description.lower().split()
        # Take first few meaningful words and join with underscores
        meaningful_words = [w for w in words[:3] if len(w) > 2 and w not in ['the', 'and', 'for', 'with']]
        agent_name = '_'.join(meaningful_words)
        if not agent_name:
            agent_name = f"agent_{int(time.time())}"
    
    # Create config directory if it doesn't exist
    config_dir = "sub_agents"
    os.makedirs(config_dir, exist_ok=True)
    
    # Try to use LLM to generate configuration
    try:
        config = _generate_config_with_llm(description, agent_name)
    except Exception as e:
        print(f"[SubAgent] Failed to generate config with LLM: {e}")
        # Fallback to basic config
        config = _generate_basic_config(description, agent_name)
    
    # Save config file if requested
    config_path = os.path.join(config_dir, f"{agent_name}.yml")
    if save_config:
        try:
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
        except Exception as e:
            print(f"[SubAgent] Warning: Failed to save config file: {e}")
    
    # Create SubAgent instance
    try:
        # Create temporary file for testing if save_config is False
        if not save_config:
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
            yaml.dump(config, temp_file, default_flow_style=False, indent=2)
            temp_file.close()
            config_path = temp_file.name
        
        sub_agent = SubAgent(config_path, tool_context=None)
        
        # Import and create AgentTool instance
        from tools.agent_tool import AgentTool
        agent_tool = AgentTool(sub_agent)
        
        return {
            "success": True,
            "sub_agent": sub_agent,
            "agent_tool": agent_tool,
            "config_path": config_path,
            "config": config
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "config_path": config_path,
            "config": config
        }


def _generate_config_with_llm(description: str, agent_name: str) -> Dict[str, Any]:
    """Generate sub-agent config using LLM."""
    from models import KimiModelClient
    
    # Use a simple config for the LLM call
    llm_config = {
        "model": "kimi-k2-0711-preview",
        "base_url": "https://api.moonshot.cn/v1",
        "max_tokens": 1000,
        "temperature": 0.1,
        "verbose": False
    }
    
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key or api_key == "mock-api-key":
        raise Exception("No API key available")
    
    model_client = KimiModelClient(llm_config)
    
    # Available tools that sub-agents can use
    available_tools = ["read_file", "edit_file"]  # Basic set for now
    
    prompt = f"""Generate a YAML configuration for a sub-agent based on this description: "{description}"

The configuration should be a valid YAML structure with these fields:
- name: "{agent_name}"
- description: A clear description of what this agent does
- system_prompt: A detailed system prompt that defines the agent's role and capabilities
- instructions: Brief instructions on when to use this agent
- available_tools: List from {available_tools} (choose appropriate tools)
- max_tokens: Number between 1000-3000
- temperature: Number between 0.1-0.7

Respond with ONLY the YAML configuration, no explanations or markdown formatting."""

    response = model_client.generate_response(prompt, [])
    config_text = response.get("content", "")
    
    # Parse the YAML response
    try:
        config = yaml.safe_load(config_text)
        if not isinstance(config, dict):
            raise ValueError("Response is not a valid YAML dictionary")
        
        # Ensure required fields
        config["name"] = agent_name
        if "available_tools" not in config:
            config["available_tools"] = ["read_file"]
        
        return config
        
    except Exception as e:
        raise Exception(f"Failed to parse LLM generated config: {e}")


def _generate_basic_config(description: str, agent_name: str) -> Dict[str, Any]:
    """Generate a basic config as fallback."""
    return {
        "name": agent_name,
        "description": description,
        "system_prompt": f"You are a specialized AI assistant for: {description}. Use the available tools to help complete tasks efficiently.",
        "instructions": f"Use this agent when you need: {description}",
        "available_tools": ["read_file"],
        "max_tokens": 2000,
        "temperature": 0.3,
        "max_iterations": 10
    }