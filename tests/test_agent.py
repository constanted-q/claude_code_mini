"""
Unit tests for the Agent class.
"""

import pytest
import os
import tempfile
import yaml
from unittest.mock import patch, mock_open

from agent import Agent


class TestAgent:
    """Test cases for the Agent class."""
    
    def test_init_with_default_config(self):
        """Test Agent initialization with default configuration."""
        with patch('builtins.open', mock_open(read_data="")):
            with patch('os.path.exists', return_value=False):
                agent = Agent()
                assert agent.config['model'] == 'gpt-4'
                assert agent.config['max_tokens'] == 4096
                assert agent.config['temperature'] == 0.2
    
    def test_init_with_custom_config_file(self):
        """Test Agent initialization with custom config file."""
        config_data = {
            'model': 'gpt-3.5-turbo',
            'max_tokens': 2048,
            'temperature': 0.5,
            'verbose': True
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            agent = Agent(config_path=config_path)
            assert agent.config['model'] == 'gpt-3.5-turbo'
            assert agent.config['max_tokens'] == 2048
            assert agent.config['temperature'] == 0.5
        finally:
            os.unlink(config_path)
    
    @patch.dict(os.environ, {'KIMI_API_KEY': 'test-api-key-123'})
    def test_init_with_env_api_key(self):
        """Test Agent initialization with API key from environment."""
        with patch('builtins.open', mock_open(read_data="")):
            with patch('os.path.exists', return_value=False):
                agent = Agent()
                assert agent.api_key == 'test-api-key-123'
    
    def test_init_without_env_api_key(self):
        """Test Agent initialization without API key in environment."""
        with patch('builtins.open', mock_open(read_data="")):
            with patch('os.path.exists', return_value=False):
                with patch.dict(os.environ, {}, clear=True):
                    agent = Agent()
                    assert agent.api_key == 'mock-api-key'
    
    def test_generate_response_hello(self):
        """Test response generation for hello messages."""
        agent = Agent()
        response = agent.generate_response("Hello there!")
        assert "Hello!" in response
        assert "Claude Code mini assistant" in response
    
    def test_generate_response_how_are_you(self):
        """Test response generation for 'how are you' messages."""
        agent = Agent()
        response = agent.generate_response("How are you doing?")
        assert "doing well" in response.lower()
        assert "thank you" in response.lower()
    
    def test_generate_response_what_can_you_do(self):
        """Test response generation for capability questions."""
        agent = Agent()
        response = agent.generate_response("What can you do?")
        assert "simple chatbot" in response.lower()
        assert "conversations" in response.lower()
    
    def test_generate_response_goodbye(self):
        """Test response generation for goodbye messages."""
        agent = Agent()
        response = agent.generate_response("Bye!")
        assert "Goodbye" in response
        assert "/exit" in response
    
    def test_generate_response_help(self):
        """Test response generation for help requests."""
        agent = Agent()
        response = agent.generate_response("I need help")
        assert "help" in response.lower()
        assert "/exit" in response
    
    def test_generate_response_generic_short(self):
        """Test response generation for short generic messages."""
        agent = Agent()
        response = agent.generate_response("Python")
        assert "Python" in response
        assert "interesting topic" in response.lower()
    
    def test_generate_response_generic_medium(self):
        """Test response generation for medium length messages."""
        agent = Agent()
        response = agent.generate_response("I really like programming in Python")
        assert "Python" in response
        assert "thoughts" in response.lower()
    
    def test_generate_response_generic_long(self):
        """Test response generation for long messages."""
        agent = Agent()
        long_message = "A message with many words that spans across multiple sentences to test " + \
                      "the response generation for longer inputs that exceed twenty words total count " + \
                      "and would trigger the detailed message response pattern in the agent code"
        response = agent.generate_response(long_message)
        assert "detailed message" in response.lower() or "quite a detailed message" in response
        assert "A" in response
    
    def test_generate_response_with_context(self):
        """Test response generation with conversation context."""
        agent = Agent()
        context = [
            {"user": "Hello", "assistant": "Hi there!"},
            {"user": "How are you?", "assistant": "I'm doing well!"}
        ]
        response = agent.generate_response("What's your name?", context)
        assert isinstance(response, str)
        assert len(response) > 0
    
    @patch('time.sleep')
    def test_generate_response_timing(self, mock_sleep):
        """Test that response generation includes simulated delay."""
        agent = Agent()
        agent.generate_response("Test message")
        mock_sleep.assert_called_once_with(0.1)
    
    def test_get_model_info(self):
        """Test getting model information."""
        agent = Agent()
        model_info = agent.get_model_info()
        
        assert 'model' in model_info
        assert 'max_tokens' in model_info
        assert 'temperature' in model_info
        assert 'has_api_key' in model_info
        
        assert model_info['model'] == 'gpt-4'
        assert model_info['max_tokens'] == 4096
        assert model_info['temperature'] == 0.2
        assert isinstance(model_info['has_api_key'], bool)
    
    @patch.dict(os.environ, {'KIMI_API_KEY': 'real-key'})
    def test_get_model_info_with_real_api_key(self):
        """Test model info with real API key."""
        with patch('builtins.open', mock_open(read_data="")):
            with patch('os.path.exists', return_value=False):
                agent = Agent()
                model_info = agent.get_model_info()
                assert model_info['has_api_key'] is True
    
    def test_load_config_file_not_found(self):
        """Test config loading when file doesn't exist."""
        agent = Agent(config_path="nonexistent.yml")
        assert agent.config == agent._default_config()
    
    def test_load_config_yaml_error(self):
        """Test config loading with invalid YAML."""
        with patch('builtins.open', mock_open(read_data="invalid: yaml: content: [")):
            with patch('yaml.safe_load', side_effect=yaml.YAMLError("Invalid YAML")):
                agent = Agent()
                assert agent.config == agent._default_config()
    
    def test_default_config(self):
        """Test default configuration values."""
        agent = Agent()
        default_config = agent._default_config()
        
        assert default_config['model'] == 'gpt-4'
        assert default_config['max_tokens'] == 4096
        assert default_config['temperature'] == 0.2
        assert default_config['verbose'] is False
    
    @patch('builtins.print')
    def test_verbose_logging(self, mock_print):
        """Test verbose logging during response generation."""
        config_data = {'verbose': True}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            agent = Agent(config_path=config_path)
            agent.generate_response("Test message")
            mock_print.assert_called()
            
            # Check that the print call contains expected verbose output
            call_args = [str(call) for call in mock_print.call_args_list]
            verbose_call_found = any("[Agent] Processing message:" in arg for arg in call_args)
            assert verbose_call_found
        finally:
            os.unlink(config_path)