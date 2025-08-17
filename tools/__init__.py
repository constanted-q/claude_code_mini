"""
Tool registry for managing available tools in the CLI agent.
"""

from typing import Dict, List, Type, Any
import importlib
import pkgutil
from .base_tool import Tool


class ToolRegistry:
    """Registry for managing and discovering available tools."""
    
    def __init__(self):
        self._tools: Dict[str, Type[Tool]] = {}
        self._instances: Dict[str, Tool] = {}
        self.auto_registered = False
    
    def register_tool(self, tool_class: Type[Tool]):
        """Register a tool class in the registry."""
        if not issubclass(tool_class, Tool):
            raise ValueError(f"Tool {tool_class} must inherit from base Tool class")
        
        tool_name = tool_class.get_name()
        if tool_name in self._tools:
            raise ValueError(f"Tool '{tool_name}' is already registered")
        
        self._tools[tool_name] = tool_class
        self._instances[tool_name] = tool_class()
    
    def get_tool(self, name: str) -> Tool:
        """Get a tool instance by name."""
        if name not in self._instances:
            raise ValueError(f"Tool '{name}' not found in registry")
        return self._instances[name]
    
    def list_tools(self) -> List[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI function schemas for all registered tools."""
        schemas = []
        for tool_instance in self._instances.values():
            schemas.append(tool_instance.to_openai_function())
        return schemas
    
    def get_tool_info(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata for all registered tools."""
        info = {}
        for name, tool_instance in self._instances.items():
            info[name] = {
                "name": tool_instance.get_name(),
                "description": tool_instance.get_description(),
                "instructions": tool_instance.get_instructions(),
                "input_schema": tool_instance.get_input_schema()
            }
        return info
    
    def auto_discover_tools(self):
        """Automatically discover and register tools in the tools package."""
        import tools
        
        # Get the tools package path
        tools_path = tools.__path__
        
        # Iterate through all modules in the tools package
        for importer, modname, ispkg in pkgutil.iter_modules(tools_path, tools.__name__ + "."):
            if modname.endswith('_tool') and not modname.endswith('base_tool'):
                try:
                    # Import the module
                    module = importlib.import_module(modname)
                    
                    # Look for Tool classes in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, Tool) and 
                            attr != Tool and
                            not attr.__name__.startswith('Base') and
                            not attr.__name__.startswith('Agent')):
                            
                            self.register_tool(attr)
                            print(f"[ToolRegistry] Auto-registered tool: {attr.get_name()}")
                            
                except Exception as e:
                    print(f"[ToolRegistry] Failed to load tool from {modname}: {e}")
        self.auto_registered = True


# Global tool registry instance
_global_registry = ToolRegistry()

def get_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return _global_registry

def register_tool(tool_class: Type[Tool]):
    """Register a tool in the global registry."""
    _global_registry.register_tool(tool_class)

def get_tool(name: str) -> Tool:
    """Get a tool instance from the global registry."""
    return _global_registry.get_tool(name)

def list_tools() -> List[str]:
    """List all available tools."""
    return _global_registry.list_tools()

def get_tool_schemas() -> List[Dict[str, Any]]:
    """Get OpenAI function schemas for all tools."""
    return _global_registry.get_tool_schemas()

def auto_discover_tools():
    """Auto-discover and register all available tools."""
    _global_registry.auto_discover_tools()