"""
Unit tests for the Session class.
"""

import pytest
from unittest.mock import Mock, patch
from session import Session


class TestSession:
    """Test cases for the Session class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_agent = Mock()
        self.mock_agent.generate_response.return_value = "Mock response"
    
    def test_init(self):
        """Test Session initialization."""
        session = Session(self.mock_agent)
        
        assert session.agent == self.mock_agent
        assert session.verbose is False
        assert session.context_history == []
        assert session.message_count == 0
    
    def test_update_context_unified_format(self):
        """Test context updating with unified format."""
        session = Session(self.mock_agent)
        
        session._update_context("Hello", "Hi there!")
        
        assert len(session.context_history) == 2  # User + assistant messages
        
        user_context = session.context_history[0]
        assert user_context["type"] == "conversation"
        assert user_context["role"] == "user"
        assert user_context["content"] == "Hello"
        
        assistant_context = session.context_history[1]
        assert assistant_context["type"] == "conversation"
        assert assistant_context["role"] == "assistant"
        assert assistant_context["content"] == "Hi there!"
    
    def test_get_filtered_context(self):
        """Test context filtering by type."""
        session = Session(self.mock_agent)
        
        session._update_context("Hello", "Hi!")
        session._update_context("How are you?", "Good!")
        
        filtered = session.get_filtered_context(["conversation"])
        
        assert len(filtered) == 4  # 2 exchanges × 2 messages each
        assert all(ctx["type"] == "conversation" for ctx in filtered)
    
    def test_context_limit(self):
        """Test context history length limiting."""
        session = Session(self.mock_agent)
        
        # Add 12 exchanges (24 messages)
        for i in range(12):
            session._update_context(f"Message {i}", f"Response {i}")
        
        # Should keep only last 20 messages (10 exchanges)
        assert len(session.context_history) == 20
        assert session.context_history[0]["content"] == "Message 2"  # First kept message
        assert session.context_history[-2]["content"] == "Message 11"  # Last user message
    
    @patch('builtins.input', side_effect=["hello", "/exit"])
    @patch('builtins.print')
    def test_start_session_basic(self, mock_print, mock_input):
        """Test basic session functionality."""
        session = Session(self.mock_agent)
        
        session.start_session()
        
        # Agent should be called with filtered context
        self.mock_agent.generate_response.assert_called_once()
        args = self.mock_agent.generate_response.call_args
        assert args[0][0] == "hello"  # Message
        assert isinstance(args[0][1], list)  # Context (initially empty)
        
        # Context should be updated
        assert len(session.context_history) == 2
        assert session.message_count == 1