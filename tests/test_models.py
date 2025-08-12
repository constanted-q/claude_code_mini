"""
Tests for the models module - KimiModelClient functionality.
"""

import os
import pytest
from unittest.mock import Mock, patch
from models import KimiModelClient


class TestKimiModelClient:
    
    def setup_method(self):
        """Setup test configuration."""
        self.config = {
            "model": "kimi-k2-0711-preview",
            "base_url": "https://api.moonshot.cn/v1",
            "max_tokens": 4096,
            "temperature": 0.2
        }
    
    @patch.dict(os.environ, {"MOONSHOT_API_KEY": "test-api-key"})
    @patch('models.OpenAI')
    def test_init_success(self, mock_openai):
        """Test successful initialization of KimiModelClient."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        client = KimiModelClient(self.config)
        
        assert client.api_key == "test-api-key"
        assert client.model == "kimi-k2-0711-preview"
        mock_openai.assert_called_once_with(
            api_key="test-api-key",
            base_url="https://api.moonshot.cn/v1"
        )
    
    @patch.dict(os.environ, {}, clear=True)
    def test_init_no_api_key(self):
        """Test initialization fails without API key."""
        with pytest.raises(ValueError, match="MOONSHOT_API_KEY environment variable is required"):
            KimiModelClient(self.config)
    
    @patch.dict(os.environ, {"MOONSHOT_API_KEY": "test-api-key"})
    @patch('models.OpenAI')
    def test_generate_response_success(self, mock_openai):
        """Test successful response generation."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is a test response."
        mock_client.chat.completions.create.return_value = mock_response
        
        client = KimiModelClient(self.config)
        response = client.generate_response("Hello")
        
        assert response == "This is a test response."
    
    @patch.dict(os.environ, {"MOONSHOT_API_KEY": "test-api-key"})
    @patch('models.OpenAI')
    def test_generate_response_api_error(self, mock_openai):
        """Test handling of API errors."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        client = KimiModelClient(self.config)
        response = client.generate_response("Hello")
        
        assert "I apologize, but I'm having trouble connecting" in response
        assert "API Error" in response