"""
Session class for handling CLI I/O, preprocessing, postprocessing, and context management.
"""

import json
import shlex
import os
import glob
from typing import List, Dict, Any, Optional
import time
from datetime import datetime
from tools import auto_discover_tools, get_registry, get_tool, register_tool


class ToolContext:
    """Context for managing tool state and cached file information."""
    
    def __init__(self):
        """Initialize empty tool context."""
        self.read_file_state: Dict[str, Dict[str, Any]] = {}
    
    def cache_file_state(self, file_path: str, content: str, encoding: str = 'utf-8'):
        """
        Cache file state after reading.
        
        Args:
            file_path: Path to the file
            content: File content (without line numbers)
            encoding: File encoding used
        """
        try:
            # Get file stats for timestamp
            stat_info = os.stat(file_path)
            
            self.read_file_state[file_path] = {
                "content": content,
                "timestamp": stat_info.st_mtime,
                "encoding": encoding,
                "size": stat_info.st_size
            }
        except OSError:
            # If we can't stat the file, store without timestamp
            self.read_file_state[file_path] = {
                "content": content,
                "timestamp": None,
                "encoding": encoding,
                "size": len(content.encode(encoding))
            }
    
    def get_cached_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get cached file state.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Cached file info or None if not cached
        """
        return self.read_file_state.get(file_path)
    
    def is_file_cached(self, file_path: str) -> bool:
        """Check if file has been cached (read)."""
        return file_path in self.read_file_state
    
    def clear_cache(self):
        """Clear all cached file states."""
        self.read_file_state.clear()


class Session:
    def __init__(self, agent, verbose: bool = False):
        """
        Initialize the Session with an Agent instance.
        
        Args:
            agent: Agent instance for generating responses
            verbose: Enable verbose logging
        """
        self.agent = agent
        self.verbose = verbose
        self.context_history: List[Dict[str, Any]] = []
        self.session_start_time = datetime.now()
        self.message_count = 0
        self.tools_enabled = True
        self.tool_context = ToolContext()
        self.sub_agents: Dict[str, Any] = {}  # Track active sub-agents
        self._initialize_tools()
        self._initialize_sub_agents()
        
    def start_session(self):
        """Start the interactive chat session."""
        self._print_welcome()
        
        while True:
            try:
                user_input = self._get_user_input()
                
                # Check for exit command
                if user_input.strip().lower() == "/exit":
                    self._print_goodbye()
                    break
                
                # Check for tool commands
                if user_input.strip().startswith("/"):
                    self._handle_special_commands(user_input.strip())
                    continue
                
                # Preprocess input
                processed_input = self._preprocess_input(user_input)
                
                if not processed_input.strip():
                    self._print_message("Please enter a message or type /exit to quit.", "system")
                    continue
                
                # Generate response using agent with filtered context and tools
                filtered_context = self.get_filtered_context(["conversation", "tool"])
                
                # Check if tools are enabled and get tool schemas
                tool_schemas = get_registry().get_tool_schemas() if self.tools_enabled else []
                
                response_data = self.agent.generate_response(processed_input, filtered_context, tool_schemas)
                
                # Handle response with potential tool calls
                final_response = self._process_agent_response(response_data, processed_input)
                
                self.message_count += 1
                
            except KeyboardInterrupt:
                print("\n")
                self._print_message("Session interrupted by user.", "system")
                self._print_goodbye()
                break
            except Exception as e:
                if self.verbose:
                    self._print_message(f"Error: {str(e)}", "error")
                else:
                    self._print_message("Sorry, I encountered an error. Please try again.", "error")
    
    def _initialize_tools(self):
        """Initialize and register available tools."""
        try:
            auto_discover_tools()
            if self.verbose:
                tools = get_registry().list_tools()
                print(f"[Session] Registered tools: {', '.join(tools)}")
        except Exception as e:
            print(f"[Session] Warning: Failed to initialize tools: {e}")
            self.tools_enabled = False
    
    def _initialize_sub_agents(self):
        """Initialize and register sub-agents from config files."""
        try:
            # Create sub_agents directory if it doesn't exist
            sub_agents_dir = "sub_agents"
            os.makedirs(sub_agents_dir, exist_ok=True)
            
            # Load existing sub-agent configs
            config_files = glob.glob(os.path.join(sub_agents_dir, "*.yml"))
            
            for config_file in config_files:
                try:
                    from tools.agent_tool import create_agent_tool_from_config
                    
                    agent_tool = create_agent_tool_from_config(config_file, self.tool_context)
                    if agent_tool:
                        # Register the agent tool instance directly
                        registry = get_registry()
                        registry._tools[agent_tool.get_name()] = type(agent_tool)
                        registry._instances[agent_tool.get_name()] = agent_tool
                        
                        # Track the sub-agent
                        sub_agent_name = agent_tool.sub_agent.name
                        self.sub_agents[sub_agent_name] = {
                            "config_path": config_file,
                            "agent_tool": agent_tool,
                            "sub_agent": agent_tool.sub_agent
                        }
                        
                        if self.verbose:
                            print(f"[Session] Loaded sub-agent: {sub_agent_name}")
                            
                except Exception as e:
                    print(f"[Session] Warning: Failed to load sub-agent from {config_file}: {e}")
                    
            if self.verbose and self.sub_agents:
                print(f"[Session] Loaded {len(self.sub_agents)} sub-agents: {', '.join(self.sub_agents.keys())}")
                
        except Exception as e:
            print(f"[Session] Warning: Failed to initialize sub-agents: {e}")
    
    def _handle_special_commands(self, command: str):
        """Handle special commands like /toolcall, /tools, etc."""
        parts = command.split(None, 1)
        cmd = parts[0].lower()
        
        if cmd == "/tools":
            self._show_available_tools()
        elif cmd == "/toggle-tools":
            self.tools_enabled = not self.tools_enabled
            status = "enabled" if self.tools_enabled else "disabled"
            self._print_message(f"Tools {status}", "system")
        elif cmd == "/agent":
            self._handle_agent_commands(command)
        elif cmd == "/help":
            self._show_help()
        else:
            self._print_message(f"Unknown command: {cmd}. Type /help for available commands.", "system")
    
    def _show_available_tools(self):
        """Show all available tools and their descriptions."""
        try:
            tool_info = get_registry().get_tool_info()
            if not tool_info:
                self._print_message("No tools available.", "system")
                return
            
            message = "Available Tools:\n"
            for name, info in tool_info.items():
                message += f"\n• {name}: {info['description']}\n"
                message += f"  Instructions: {info['instructions']}\n"
            
            self._print_message(message, "system")
        except Exception as e:
            self._print_message(f"Error listing tools: {e}", "error")
    
    def _show_help(self):
        """Show help for available commands."""
        help_text = """Available Commands:
        
• /exit - Quit the session
• /tools - List all available tools
• /toggle-tools - Enable/disable tool use
• /agent - List all sub-agents
• /agent -new <description> - Create new sub-agent
• /agent -delete <name> - Delete sub-agent
• /help - Show this help message

Tool Usage:
When tools are enabled, the AI assistant can automatically use tools to help answer your questions.
You can also call tools directly using /toolcall command.
        """
        self._print_message(help_text, "system")
    
    def _handle_agent_commands(self, command: str):
        """Handle /agent commands for sub-agent management."""
        parts = command.split()
        
        if len(parts) == 1:
            # /agent - list all sub-agents
            self._list_sub_agents()
        elif len(parts) >= 3 and parts[1] == "-new":
            # /agent -new <description> - create new sub-agent
            description = " ".join(parts[2:])
            self._create_new_sub_agent(description)
        elif len(parts) == 3 and parts[1] == "-delete":
            # /agent -delete <name> - delete sub-agent
            agent_name = parts[2]
            self._delete_sub_agent(agent_name)
        else:
            self._print_message("Usage: /agent [-new <description>] [-delete <name>]", "system")
    
    def _list_sub_agents(self):
        """List all available sub-agents."""
        if not self.sub_agents:
            self._print_message("No sub-agents available. Use '/agent -new <description>' to create one.", "system")
            return
        
        message = f"Available Sub-Agents ({len(self.sub_agents)}):\n"
        for name, info in self.sub_agents.items():
            sub_agent = info["sub_agent"]
            message += f"\n• {name}: {sub_agent.description}\n"
            message += f"  Tools: {', '.join(sub_agent.available_tools)}\n"
            message += f"  Instructions: {sub_agent.instructions}\n"
        
        self._print_message(message, "system")
    
    def _create_new_sub_agent(self, description: str):
        """Create a new sub-agent from description."""
        if not description.strip():
            self._print_message("Please provide a description for the sub-agent.", "error")
            return
        
        try:
            from sub_agent import create_sub_agent
            
            self._print_message(f"Creating sub-agent for: {description}", "system")
            
            result = create_sub_agent(description, save_config=True)
            
            if result.get("success", False):
                sub_agent = result["sub_agent"]
                agent_tool = result["agent_tool"]
                
                # Register the agent tool instance directly
                registry = get_registry()
                registry._tools[agent_tool.get_name()] = type(agent_tool)
                registry._instances[agent_tool.get_name()] = agent_tool
                
                # Track the sub-agent
                self.sub_agents[sub_agent.name] = {
                    "config_path": result["config_path"],
                    "agent_tool": agent_tool,
                    "sub_agent": sub_agent
                }
                
                self._print_message(
                    f"✅ Created sub-agent '{sub_agent.name}' successfully!\n"
                    f"Description: {sub_agent.description}\n"
                    f"Available tools: {', '.join(sub_agent.available_tools)}\n"
                    f"Config saved to: {result['config_path']}",
                    "system"
                )
            else:
                error_msg = result.get("error", "Unknown error")
                self._print_message(f"❌ Failed to create sub-agent: {error_msg}", "error")
                
        except Exception as e:
            self._print_message(f"❌ Error creating sub-agent: {str(e)}", "error")
    
    def _delete_sub_agent(self, agent_name: str):
        """Delete a sub-agent."""
        if agent_name not in self.sub_agents:
            self._print_message(f"Sub-agent '{agent_name}' not found.", "error")
            return
        
        try:
            # Get config path
            config_path = self.sub_agents[agent_name]["config_path"]
            
            # Remove from registry (best effort)
            try:
                agent_tool = self.sub_agents[agent_name]["agent_tool"]
                tool_name = agent_tool.get_name()
                # Note: ToolRegistry doesn't have unregister method, so we just remove from our tracking
            except:
                pass
            
            # Remove config file
            if os.path.exists(config_path):
                os.remove(config_path)
            
            # Remove from tracking
            del self.sub_agents[agent_name]
            
            self._print_message(f"✅ Deleted sub-agent '{agent_name}' successfully.", "system")
            
        except Exception as e:
            self._print_message(f"❌ Error deleting sub-agent: {str(e)}", "error")
    
    def _process_agent_response(self, response_data: Dict[str, Any], user_input: str) -> str:
        """Process agent response, handling tool calls if present."""
        # Check if response contains tool calls
        if "tool_calls" in response_data and response_data["tool_calls"]:
            return self._handle_tool_calls(response_data, user_input)
        else:
            # Regular text response
            response_text = response_data.get("content", "")
            processed_response = self._postprocess_response(response_text)
            
            # Display and update context
            self._print_message(processed_response, "assistant")
            self._update_context(user_input, processed_response)
            
            return processed_response
    
    def _handle_tool_calls(self, response_data: Dict[str, Any], user_input: str) -> str:
        """Handle tool calls from agent response."""
        assistant_message = response_data.get("content", "")
        tool_calls = response_data.get("tool_calls", [])

        # Update context with initial user input and assistant response
        self._update_context(user_input, assistant_message, tool_calls)
        
        # Display initial assistant message if present
        if assistant_message:
            self._print_message(assistant_message, "assistant")
        
        # Execute each tool call
        tool_results = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            tool_args = tool_call.get("function", {}).get("arguments", {})
            call_id = tool_call.get("id", "")
            print(f"###debug: call_id {call_id} in session 225")
            
            if self.verbose:
                print(f"[Session] Executing tool: {tool_name} with args: {tool_args}")
            
            try:
                # Get and execute tool
                tool = get_tool(tool_name)
                result = tool.safe_execute(tool_context=self.tool_context, **tool_args)
                
                # Show tool execution result
                if result.success:
                    self._print_message(f"🔧 Tool '{tool_name}' executed:\n{result.content}", "tool")
                else:
                    self._print_message(f"⚠️ Tool '{tool_name}' failed: {result.error}", "error")
                
                # Add to context and results
                tool_context = tool.to_unified_context(result, call_id)
                self.context_history.append(tool_context)
                tool_results.append(tool_context)
                
            except Exception as e:
                error_msg = f"Error executing tool {tool_name}: {e}"
                self._print_message(error_msg, "error")
                
                # Add error to context
                error_context = {
                    "type": "tool",
                    "role": "tool",
                    "content": f"Error: {error_msg}",
                    "metadata": {
                        "tool_name": tool_name,
                        "success": False,
                        "error": error_msg,
                        "tool_call_id": call_id
                    }
                }
                self.context_history.append(error_context)
                tool_results.append(error_context)
        

        
        # Check if we need to continue the conversation with tool results
        if tool_results:
            # Generate follow-up response with tool results
            follow_up_context = self.get_filtered_context(["conversation", "tool"])
            tool_schemas = get_registry().get_tool_schemas() if self.tools_enabled else []
            
            follow_up_response = self.agent.generate_response(
                "Continue based on the tool results above.", 
                follow_up_context, 
                tool_schemas
            )
            
            # Process follow-up response (could contain more tool calls)
            if isinstance(follow_up_response, dict) and "tool_calls" in follow_up_response:
                return self._handle_tool_calls(follow_up_response, "")
            else:
                final_text = follow_up_response if isinstance(follow_up_response, str) else follow_up_response.get("content", "")
                processed_final = self._postprocess_response(final_text)
                self._print_message(processed_final, "assistant")
                
                # Add final response to context
                self._add_assistant_context(processed_final)
                
                return processed_final
        
        return assistant_message

    def _get_user_input(self) -> str:
        """Get input from the user with a nice prompt."""
        try:
            return input("\n🟢 You: ")
        except EOFError:
            return "/exit"
    
    def _preprocess_input(self, user_input: str) -> str:
        """
        Preprocess user input before sending to agent.
        
        Args:
            user_input: Raw user input
            
        Returns:
            Processed input string
        """
        # Strip whitespace
        processed = user_input.strip()
        
        # Log preprocessing if verbose
        if self.verbose and processed != user_input:
            print(f"[Session] Preprocessed input: '{user_input}' -> '{processed}'")
        
        return processed
    
    def _postprocess_response(self, response: str) -> str:
        """
        Postprocess agent response before displaying.
        
        Args:
            response: Raw agent response
            
        Returns:
            Processed response string
        """
        # Strip whitespace and ensure proper formatting
        processed = response.strip()
        
        # Add period if response doesn't end with punctuation
        if processed and not processed.endswith(('.', '!', '?', ':')):
            processed += '.'
        
        # Log postprocessing if verbose
        if self.verbose and processed != response:
            print(f"[Session] Postprocessed response: '{response}' -> '{processed}'")
        
        return processed
    
    def _update_context(self, user_input: str, agent_response: str, tool_calls: List[Dict[str, Any]] = None):
        """
        Update the conversation context history using unified context format.
        
        Args:
            user_input: User's message
            agent_response: Agent's response
            tool_calls: Optional tool calls made by the agent
        """
        new_messages = []
        timestamp = datetime.now().isoformat()
        message_id = len(self.context_history) + 1
        if user_input:
            # Add user message in unified format
            user_context = {
                "type": "conversation",
                "role": "user",
                "content": user_input,
                "metadata": {
                    "timestamp": timestamp,
                    "message_id": f"{message_id}_user"
                }
            }
            new_messages.append(user_context)
        if agent_response:
            # Add assistant message in unified format
            assistant_context = {
                "type": "conversation",
                "role": "assistant",
                "content": agent_response,
                "metadata": {
                    "timestamp": timestamp,
                    "message_id": f"{message_id}_assistant"
                }
            }
            # Add tool calls to metadata if present
            if tool_calls:
                assistant_context["metadata"]["tool_calls"] = tool_calls
            new_messages.append(assistant_context)
        # Add both messages to context history
        self.context_history.extend(new_messages)
        
        # Keep only last 30 entries to prevent context overflow (increased for tool contexts)
        if len(self.context_history) > 100:
            self.context_history = self.context_history[-100:]
        
        if self.verbose:
            print(f"[Session] Context updated. History length: {len(self.context_history)}")
    
    def _add_assistant_context(self, response: str):
        """Add assistant response to context without user input."""
        timestamp = datetime.now().isoformat()
        message_id = len(self.context_history) + 1
        
        assistant_context = {
            "type": "conversation", 
            "role": "assistant",
            "content": response,
            "metadata": {
                "timestamp": timestamp,
                "message_id": f"{message_id}_assistant"
            }
        }
        
        self.context_history.append(assistant_context)
        
        if len(self.context_history) > 30:
            self.context_history = self.context_history[-30:]
    
    def get_filtered_context(self, context_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get context filtered by type(s) for future extensibility.
        
        Args:
            context_types: List of context types to include (default: ["conversation"])
            
        Returns:
            Filtered context history
        """
        if context_types is None:
            context_types = ["conversation"]
        
        return [ctx for ctx in self.context_history if ctx.get("type") in context_types]
    
    def _print_welcome(self):
        """Print welcome message."""
        print("\n" + "="*60)
        print("🤖 Welcome to Claude Code Mini!")
        print("="*60)
        print("Type your messages below. Use '/exit' to quit.")
        print("Type '/help' for available commands and '/tools' to list tools.")
        
        # Show if tools are available
        try:
            tools = get_registry().list_tools()
            if tools:
                print(f"Tools available: {', '.join(tools)}")
        except:
            pass
            
        print("-"*60)
    
    def _print_goodbye(self):
        """Print goodbye message with session stats."""
        session_duration = datetime.now() - self.session_start_time
        print("\n" + "-"*60)
        print("👋 Goodbye! Session Summary:")
        print(f"   • Duration: {session_duration.seconds} seconds")
        print(f"   • Messages exchanged: {self.message_count}")
        print(f"   • Context entries: {len(self.context_history)}")
        print("="*60)
    
    def _print_message(self, message: str, sender: str = "assistant"):
        """
        Print a message with appropriate formatting.
        
        Args:
            message: Message to print
            sender: Who is sending the message (assistant, system, error, tool)
        """
        if sender == "assistant":
            print(f"\n🤖 Assistant: {message}")
        elif sender == "system":
            print(f"\n💬 System: {message}")
        elif sender == "error":
            print(f"\n❌ Error: {message}")
        elif sender == "tool":
            print(f"\n{message}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Return current session statistics."""
        return {
            "start_time": self.session_start_time.isoformat(),
            "duration_seconds": (datetime.now() - self.session_start_time).seconds,
            "message_count": self.message_count,
            "context_length": len(self.context_history),
            "agent_info": self.agent.get_model_info()
        }
    
    def clear_context(self):
        """Clear the conversation context history."""
        self.context_history.clear()
        if self.verbose:
            print("[Session] Context history cleared.")