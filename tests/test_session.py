"""
Unit tests for the Session class.
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime
from io import StringIO
import sys

from session import Session
from agent import Agent


class TestSession:
    """Test cases for the Session class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_agent = Mock(spec=Agent)
        self.mock_agent.generate_response.return_value = "Mock response"
        self.mock_agent.get_model_info.return_value = {
            "model": "test-model",
            "max_tokens": 1000,
            "temperature": 0.5,
            "has_api_key": True
        }
    
    def test_init(self):
        """Test Session initialization."""
        session = Session(self.mock_agent)
        
        assert session.agent == self.mock_agent
        assert session.verbose is False
        assert session.context_history == []
        assert session.message_count == 0
        assert isinstance(session.session_start_time, datetime)
    
    def test_init_verbose(self):
        """Test Session initialization with verbose enabled."""
        session = Session(self.mock_agent, verbose=True)
        assert session.verbose is True
    
    def test_preprocess_input(self):
        """Test input preprocessing."""
        session = Session(self.mock_agent)
        
        # Test whitespace stripping
        assert session._preprocess_input("  hello world  ") == "hello world"
        assert session._preprocess_input("\n\ttest\n\t") == "test"
        assert session._preprocess_input("") == ""
    
    @patch('builtins.print')
    def test_preprocess_input_verbose(self, mock_print):
        """Test input preprocessing with verbose logging."""
        session = Session(self.mock_agent, verbose=True)
        
        result = session._preprocess_input("  hello  ")
        
        assert result == "hello"
        mock_print.assert_called_with("[Session] Preprocessed input: '  hello  ' -> 'hello'")
    
    def test_postprocess_response(self):
        """Test response postprocessing."""
        session = Session(self.mock_agent)
        
        # Test whitespace stripping
        assert session._postprocess_response("  hello world  ") == "hello world."
        
        # Test period addition
        assert session._postprocess_response("hello") == "hello."
        assert session._postprocess_response("hello!") == "hello!"
        assert session._postprocess_response("hello?") == "hello?"
        assert session._postprocess_response("hello:") == "hello:"
        assert session._postprocess_response("hello.") == "hello."
        
        # Test empty string
        assert session._postprocess_response("") == ""
    
    @patch('builtins.print')
    def test_postprocess_response_verbose(self, mock_print):
        """Test response postprocessing with verbose logging."""
        session = Session(self.mock_agent, verbose=True)
        
        result = session._postprocess_response("hello")
        
        assert result == "hello."
        mock_print.assert_called_with("[Session] Postprocessed response: 'hello' -> 'hello.'")
    
    def test_update_context(self):
        """Test context history updates."""
        session = Session(self.mock_agent)
        
        session._update_context("Hello", "Hi there")
        
        assert len(session.context_history) == 1
        entry = session.context_history[0]
        
        assert entry['user'] == "Hello"
        assert entry['assistant'] == "Hi there"
        assert entry['message_id'] == 1
        assert 'timestamp' in entry
    
    @patch('builtins.print')
    def test_update_context_verbose(self, mock_print):
        """Test context updates with verbose logging."""
        session = Session(self.mock_agent, verbose=True)
        
        session._update_context("Hello", "Hi")
        
        mock_print.assert_called_with("[Session] Context updated. History length: 1")
    
    def test_update_context_limit(self):
        """Test context history length limiting."""
        session = Session(self.mock_agent)
        
        # Add 12 entries (should keep only last 10)
        for i in range(12):
            session._update_context(f"Message {i}", f"Response {i}")
        
        assert len(session.context_history) == 10
        # Should have messages 2-11 (0-indexed, so first entry should be message 2)
        assert session.context_history[0]['user'] == "Message 2"
        assert session.context_history[-1]['user'] == "Message 11"
    
    def test_get_session_stats(self):
        """Test getting session statistics."""
        session = Session(self.mock_agent)
        session.message_count = 5
        session._update_context("Test", "Response")
        
        stats = session.get_session_stats()
        
        assert 'start_time' in stats
        assert 'duration_seconds' in stats
        assert stats['message_count'] == 5
        assert stats['context_length'] == 1
        assert 'agent_info' in stats
        assert stats['agent_info']['model'] == "test-model"
    
    def test_clear_context(self):
        """Test clearing context history."""
        session = Session(self.mock_agent)
        session._update_context("Test", "Response")
        
        assert len(session.context_history) == 1
        
        session.clear_context()
        
        assert len(session.context_history) == 0
    
    @patch('builtins.print')
    def test_clear_context_verbose(self, mock_print):
        """Test clearing context with verbose logging."""
        session = Session(self.mock_agent, verbose=True)
        session._update_context("Test", "Response")
        
        session.clear_context()
        
        mock_print.assert_called_with("[Session] Context history cleared.")
    
    @patch('builtins.print')
    def test_print_message_assistant(self, mock_print):
        """Test printing assistant messages."""
        session = Session(self.mock_agent)
        
        session._print_message("Hello world", "assistant")
        
        mock_print.assert_called_with("\n🤖 Assistant: Hello world")
    
    @patch('builtins.print')
    def test_print_message_system(self, mock_print):
        """Test printing system messages."""
        session = Session(self.mock_agent)
        
        session._print_message("System message", "system")
        
        mock_print.assert_called_with("\n💬 System: System message")
    
    @patch('builtins.print')
    def test_print_message_error(self, mock_print):
        """Test printing error messages."""
        session = Session(self.mock_agent)
        
        session._print_message("Error occurred", "error")
        
        mock_print.assert_called_with("\n❌ Error: Error occurred")
    
    @patch('builtins.print')
    def test_print_welcome(self, mock_print):
        """Test printing welcome message."""
        session = Session(self.mock_agent)
        
        session._print_welcome()
        
        # Check that welcome message components are printed
        call_args = [str(call) for call in mock_print.call_args_list]
        welcome_found = any("Welcome to Claude Code Mini!" in arg for arg in call_args)
        exit_instruction_found = any("'/exit'" in arg for arg in call_args)
        
        assert welcome_found
        assert exit_instruction_found
    
    @patch('builtins.print')
    def test_print_goodbye(self, mock_print):
        """Test printing goodbye message."""
        session = Session(self.mock_agent)
        session.message_count = 3
        session._update_context("Test1", "Response1")
        session._update_context("Test2", "Response2")
        
        session._print_goodbye()
        
        # Check that goodbye components are printed
        call_args = [str(call) for call in mock_print.call_args_list]
        goodbye_found = any("Goodbye!" in arg for arg in call_args)
        messages_found = any("Messages exchanged: 3" in arg for arg in call_args)
        context_found = any("Context entries: 2" in arg for arg in call_args)
        
        assert goodbye_found
        assert messages_found
        assert context_found
    
    @patch('builtins.input', side_effect=["/exit"])
    @patch('builtins.print')
    def test_start_session_immediate_exit(self, mock_print, mock_input):
        """Test starting session with immediate exit."""
        session = Session(self.mock_agent)
        
        session.start_session()
        
        # Should print welcome and goodbye but no agent responses
        self.mock_agent.generate_response.assert_not_called()
        
        # Check that goodbye was called
        call_args = [str(call) for call in mock_print.call_args_list]
        goodbye_found = any("Goodbye!" in arg for arg in call_args)
        assert goodbye_found
    
    @patch('builtins.input', side_effect=["hello", "/exit"])
    @patch('builtins.print')
    def test_start_session_single_exchange(self, mock_print, mock_input):
        """Test session with single message exchange."""
        session = Session(self.mock_agent)
        
        session.start_session()
        
        # Should have called agent once
        self.mock_agent.generate_response.assert_called_once()
        
        # Check session state
        assert session.message_count == 1
        assert len(session.context_history) == 1
        assert session.context_history[0]['user'] == "hello"
        assert session.context_history[0]['assistant'] == "Mock response."

    
    @patch('builtins.input', side_effect=KeyboardInterrupt())
    @patch('builtins.print')
    def test_start_session_keyboard_interrupt(self, mock_print, mock_input):
        """Test session handling of keyboard interrupt."""
        session = Session(self.mock_agent)
        
        session.start_session()
        
        # Should handle interrupt gracefully
        call_args = [str(call) for call in mock_print.call_args_list]
        interrupt_found = any("interrupted by user" in arg for arg in call_args)
        goodbye_found = any("Goodbye!" in arg for arg in call_args)
        
        assert interrupt_found
        assert goodbye_found
    
    @patch('builtins.input', side_effect=["hello", "/exit"])
    @patch('builtins.print')
    def test_start_session_agent_exception(self, mock_print, mock_input):
        """Test session handling of agent exceptions."""
        self.mock_agent.generate_response.side_effect = Exception("Test error")
        session = Session(self.mock_agent)
        
        session.start_session()
        
        # Should handle error and continue
        call_args = [str(call) for call in mock_print.call_args_list]
        error_found = any("encountered an error" in arg for arg in call_args)
        assert error_found
    
    @patch('builtins.input', side_effect=["hello", "/exit"])
    @patch('builtins.print')
    def test_start_session_agent_exception_verbose(self, mock_print, mock_input):
        """Test session handling of agent exceptions in verbose mode."""
        self.mock_agent.generate_response.side_effect = Exception("Test error")
        session = Session(self.mock_agent, verbose=True)
        
        session.start_session()
        
        # Should show actual error in verbose mode
        call_args = [str(call) for call in mock_print.call_args_list]
        error_found = any("Error: Test error" in arg for arg in call_args)
        assert error_found
    
    @patch('builtins.input', side_effect=EOFError())
    @patch('builtins.print')
    def test_get_user_input_eof(self, mock_print, mock_input):
        """Test handling of EOF in user input."""
        session = Session(self.mock_agent)
        
        result = session._get_user_input()
        assert result == "/exit"