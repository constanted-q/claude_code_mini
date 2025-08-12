"""
Unit tests for the Agent class.
"""

import pytest
import os
import tempfile
import yaml
from unittest.mock import patch, mock_open, Mock

from agent import Agent


class TestAgent:
    """Test cases for the Agent class."""
    
    @patch('agent.KimiModelClient')
    def test_init_with_default_config(self, mock_model_client):
        """Test Agent initialization with default configuration."""
        with patch('builtins.open', mock_open(read_data="")):
            with patch('os.path.exists', return_value=False):
                with patch.dict(os.environ, {}, clear=True):
                    agent = Agent()
                    assert agent.config['model'] == 'kimi-k2-0711-preview'
                    assert agent.use_real_model is False
    
    @patch('agent.KimiModelClient')
    @patch.dict(os.environ, {'MOONSHOT_API_KEY': 'test-api-key-123'})
    def test_init_with_env_api_key(self, mock_model_client):
        """Test Agent initialization with API key from environment."""
        mock_client_instance = Mock()
        mock_model_client.return_value = mock_client_instance
        
        with patch('builtins.open', mock_open(read_data="")):
            with patch('os.path.exists', return_value=False):
                agent = Agent()
                assert agent.api_key == 'test-api-key-123'
                assert agent.use_real_model is True
    
    @patch('agent.KimiModelClient')
    def test_generate_response_mock(self, mock_model_client):
        """Test response generation with mock fallback."""
        with patch.dict(os.environ, {}, clear=True):
            agent = Agent()
            response = agent.generate_response("Hello there!")
            assert "Hello!" in response
            assert "Claude Code mini assistant" in response
    
    @patch('agent.KimiModelClient')
    @patch.dict(os.environ, {'MOONSHOT_API_KEY': 'test-api-key'})
    def test_generate_response_with_real_model(self, mock_model_client):
        """Test response generation with real model client."""
        mock_client_instance = Mock()
        mock_client_instance.generate_response.return_value = "This is a real API response"
        mock_model_client.return_value = mock_client_instance
        
        with patch('builtins.open', mock_open(read_data="")):
            with patch('os.path.exists', return_value=False):
                agent = Agent()
                response = agent.generate_response("Test message")
                
                assert response == "This is a real API response"
                mock_client_instance.generate_response.assert_called_once()
    
    @patch('agent.KimiModelClient')
    def test_get_model_info_mock(self, mock_model_client):
        """Test getting model information in mock mode."""
        with patch.dict(os.environ, {}, clear=True):
            agent = Agent()
            model_info = agent.get_model_info()
            
            assert model_info['model'] == 'kimi-k2-0711-preview'
            assert model_info['using_mock'] is True
    
    @patch('agent.KimiModelClient')
    @patch.dict(os.environ, {'MOONSHOT_API_KEY': 'real-key'})
    def test_get_model_info_with_real_api_key(self, mock_model_client):
        """Test model info with real API key."""
        mock_client_instance = Mock()
        mock_client_instance.get_model_info.return_value = {
            'model': 'kimi-k2-0711-preview',
            'base_url': 'https://api.moonshot.cn/v1',
            'max_tokens': 4096,
            'temperature': 0.2,
            'has_api_key': True
        }
        mock_model_client.return_value = mock_client_instance
        
        with patch('builtins.open', mock_open(read_data="")):
            with patch('os.path.exists', return_value=False):
                agent = Agent()
                model_info = agent.get_model_info()
                assert model_info['has_api_key'] is True
                assert 'using_mock' not in model_info