"""
Session class for handling CLI I/O, preprocessing, postprocessing, and context management.
"""

from typing import List, Dict, Any, Optional
import time
from datetime import datetime


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
                
                # Preprocess input
                processed_input = self._preprocess_input(user_input)
                
                if not processed_input.strip():
                    self._print_message("Please enter a message or type /exit to quit.", "system")
                    continue
                
                # Generate response using agent
                response = self.agent.generate_response(processed_input, self.context_history)
                
                # Postprocess response
                processed_response = self._postprocess_response(response)
                
                # Display response
                self._print_message(processed_response, "assistant")
                
                # Update context
                self._update_context(processed_input, processed_response)
                
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
    
    def _update_context(self, user_input: str, agent_response: str):
        """
        Update the conversation context history.
        
        Args:
            user_input: User's message
            agent_response: Agent's response
        """
        context_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "assistant": agent_response,
            "message_id": len(self.context_history) + 1
        }
        
        self.context_history.append(context_entry)
        
        # Keep only last 10 exchanges to prevent context overflow
        if len(self.context_history) > 10:
            self.context_history.pop(0)
        
        if self.verbose:
            print(f"[Session] Context updated. History length: {len(self.context_history)}")
    
    def _print_welcome(self):
        """Print welcome message."""
        print("\n" + "="*60)
        print("🤖 Welcome to Claude Code Mini!")
        print("="*60)
        print("Type your messages below. Use '/exit' to quit.")
        print("This is a simple chatbot implementation with mocked responses.")
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
            sender: Who is sending the message (assistant, system, error)
        """
        if sender == "assistant":
            print(f"\n🤖 Assistant: {message}")
        elif sender == "system":
            print(f"\n💬 System: {message}")
        elif sender == "error":
            print(f"\n❌ Error: {message}")
    
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