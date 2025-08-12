"""
Integration tests for the CLI functionality of Claude Code Mini.
"""

import pytest
import sys
import os
import tempfile
import yaml
from unittest.mock import patch, Mock, call
from io import StringIO

# Import the main module
import claude_code_mini
from agent import Agent
from session import Session


class TestCLI:
    """Integration tests for CLI functionality."""
    
    def test_parse_arguments_defaults(self):
        """Test argument parsing with default values."""
        with patch('sys.argv', ['claude_code_mini.py']):
            args = claude_code_mini.parse_arguments()
            
            assert args.config == 'config.yml'
            assert args.verbose is False
    
    def test_parse_arguments_custom(self):
        """Test argument parsing with custom values."""
        with patch('sys.argv', ['claude_code_mini.py', '--config', 'custom.yml', '--verbose']):
            args = claude_code_mini.parse_arguments()
            
            assert args.config == 'custom.yml'
            assert args.verbose is True
    
    def test_parse_arguments_short_flags(self):
        """Test argument parsing with short flags."""
        with patch('sys.argv', ['claude_code_mini.py', '-c', 'test.yml', '-v']):
            args = claude_code_mini.parse_arguments()
            
            assert args.config == 'test.yml'
            assert args.verbose is True
    
    def test_parse_arguments_version(self):
        """Test version argument."""
        with patch('sys.argv', ['claude_code_mini.py', '--version']):
            with pytest.raises(SystemExit):
                claude_code_mini.parse_arguments()
    
    @patch('yaml.safe_load')
    def test_check_dependencies_success(self, mock_yaml):
        """Test successful dependency checking."""
        # Should not raise any exception
        claude_code_mini.check_dependencies()
    
    @patch('builtins.__import__', side_effect=lambda name, *args, **kwargs: 
           __import__(name, *args, **kwargs) if name != 'yaml' else (_ for _ in ()).throw(ImportError()))
    @patch('sys.exit')
    @patch('builtins.print')
    def test_check_dependencies_failure(self, mock_print, mock_exit, mock_import):
        """Test dependency checking failure."""
        claude_code_mini.check_dependencies()
        
        mock_print.assert_any_call("❌ Error: PyYAML is required but not installed.")
        mock_print.assert_any_call("Please install it with: pip install pyyaml")
        mock_exit.assert_called_with(1)
    
    @patch('claude_code_mini.Session')
    @patch('claude_code_mini.Agent')
    @patch('sys.argv', ['claude_code_mini.py'])
    @patch('builtins.print')
    def test_main_normal_execution(self, mock_print, mock_agent_class, mock_session_class):
        """Test normal main execution flow."""
        # Set up mocks
        mock_agent = Mock()
        mock_agent.get_model_info.return_value = {
            'model': 'test-model',
            'max_tokens': 1000,
            'temperature': 0.5,
            'has_api_key': True
        }
        mock_agent_class.return_value = mock_agent
        
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Run main
        claude_code_mini.main()
        
        # Verify execution flow
        mock_agent_class.assert_called_once_with(config_path='config.yml')
        mock_session_class.assert_called_once_with(mock_agent, verbose=False)
        mock_session.start_session.assert_called_once()
        
        # Check header output
        call_args = [str(call) for call in mock_print.call_args_list]
        header_found = any("Claude Code Mini v0.1.0" in arg for arg in call_args)
        exit_instruction_found = any("'/exit'" in arg for arg in call_args)
        assert header_found
        assert exit_instruction_found
    
    @patch('claude_code_mini.Session')
    @patch('claude_code_mini.Agent')
    @patch('sys.argv', ['claude_code_mini.py', '--verbose'])
    @patch('builtins.print')
    def test_main_verbose_execution(self, mock_print, mock_agent_class, mock_session_class):
        """Test main execution with verbose flag."""
        # Set up mocks
        mock_agent = Mock()
        mock_agent.get_model_info.return_value = {
            'model': 'gpt-4',
            'max_tokens': 4096,
            'temperature': 0.2,
            'has_api_key': False
        }
        mock_agent_class.return_value = mock_agent
        
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Run main
        claude_code_mini.main()
        
        # Verify verbose output
        call_args = [str(call) for call in mock_print.call_args_list]
        config_loading_found = any("[CLI] Loading configuration from: config.yml" in arg for arg in call_args)
        model_info_found = any("[CLI] Model: gpt-4" in arg for arg in call_args)
        tokens_info_found = any("[CLI] Max tokens: 4096" in arg for arg in call_args)
        temp_info_found = any("[CLI] Temperature: 0.2" in arg for arg in call_args)
        api_key_info_found = any("[CLI] API key configured: False" in arg for arg in call_args)
        
        assert config_loading_found
        assert model_info_found
        assert tokens_info_found
        assert temp_info_found
        assert api_key_info_found
        
        # Verify verbose session creation
        mock_session_class.assert_called_once_with(mock_agent, verbose=True)
    
    @patch('claude_code_mini.Session')
    @patch('claude_code_mini.Agent')
    @patch('sys.argv', ['claude_code_mini.py', '--config', 'custom.yml'])
    @patch('builtins.print')
    def test_main_custom_config(self, mock_print, mock_agent_class, mock_session_class):
        """Test main execution with custom config file."""
        # Set up mocks
        mock_agent = Mock()
        mock_agent.get_model_info.return_value = {'model': 'test', 'max_tokens': 1000, 'temperature': 0.5, 'has_api_key': True}
        mock_agent_class.return_value = mock_agent
        
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Run main
        claude_code_mini.main()
        
        # Verify custom config is used
        mock_agent_class.assert_called_once_with(config_path='custom.yml')
    
    @patch('claude_code_mini.Session')
    @patch('claude_code_mini.Agent', side_effect=Exception("Config error"))
    @patch('sys.argv', ['claude_code_mini.py'])
    @patch('sys.exit')
    @patch('builtins.print')
    def test_main_agent_initialization_error(self, mock_print, mock_exit, mock_agent_class, mock_session_class):
        """Test main handling of agent initialization errors."""
        claude_code_mini.main()
        
        mock_exit.assert_called_with(1)
        call_args = [str(call) for call in mock_print.call_args_list]
        error_found = any("Error: Config error" in arg for arg in call_args)
        assert error_found
    
    @patch('claude_code_mini.Session')
    @patch('claude_code_mini.Agent', side_effect=Exception("Config error"))
    @patch('sys.argv', ['claude_code_mini.py', '--verbose'])
    @patch('sys.exit')
    @patch('builtins.print')
    def test_main_agent_initialization_error_verbose(self, mock_print, mock_exit, mock_agent_class, mock_session_class):
        """Test main handling of agent initialization errors in verbose mode."""
        with patch('traceback.print_exc') as mock_traceback:
            claude_code_mini.main()
        
        mock_exit.assert_called_with(1)
        call_args = [str(call) for call in mock_print.call_args_list]
        error_found = any("Fatal error: Config error" in arg for arg in call_args)
        assert error_found
        mock_traceback.assert_called_once()
    
    @patch('claude_code_mini.Session')
    @patch('claude_code_mini.Agent')
    @patch('sys.argv', ['claude_code_mini.py'])
    @patch('sys.exit')
    @patch('builtins.print')
    def test_main_keyboard_interrupt(self, mock_print, mock_exit, mock_agent_class, mock_session_class):
        """Test main handling of keyboard interrupt."""
        # Set up mocks
        mock_session = Mock()
        mock_session.start_session.side_effect = KeyboardInterrupt()
        mock_session_class.return_value = mock_session
        
        claude_code_mini.main()
        
        mock_exit.assert_called_with(0)
        call_args = [str(call) for call in mock_print.call_args_list]
        goodbye_found = any("Goodbye!" in arg for arg in call_args)
        assert goodbye_found
    
    @patch('claude_code_mini.Session')
    @patch('claude_code_mini.Agent')
    @patch('sys.argv', ['claude_code_mini.py'])
    def test_main_session_execution_error(self, mock_agent_class, mock_session_class):
        """Test main handling of session execution errors."""
        # Set up mocks
        mock_session = Mock()
        mock_session.start_session.side_effect = RuntimeError("Session error")
        mock_session_class.return_value = mock_session
        
        with patch('sys.exit') as mock_exit, patch('builtins.print') as mock_print:
            claude_code_mini.main()
        
        mock_exit.assert_called_with(1)
        call_args = [str(call) for call in mock_print.call_args_list]
        error_found = any("Error: Session error" in arg for arg in call_args)
        assert error_found


class TestCLIIntegration:
    """Higher-level integration tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary config file
        self.config_data = {
            'model': 'test-model',
            'max_tokens': 1000,
            'temperature': 0.3,
            'verbose': False
        }
        
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
        yaml.dump(self.config_data, self.temp_config)
        self.temp_config.close()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_config.name):
            os.unlink(self.temp_config.name)
    
    @patch('builtins.input', side_effect=["hello", "/exit"])
    @patch('builtins.print')
    def test_full_integration_single_exchange(self, mock_print, mock_input):
        """Test full integration with single message exchange."""
        with patch('sys.argv', ['claude_code_mini.py', '--config', self.temp_config.name]):
            claude_code_mini.main()
        
        # Verify that session ran and processed input
        call_args = [str(call) for call in mock_print.call_args_list]
        
        # Should have welcome message
        welcome_found = any("Welcome to Claude Code Mini!" in arg for arg in call_args)
        assert welcome_found
        
        # Should have assistant response
        assistant_response_found = any("🤖 Assistant:" in arg for arg in call_args)
        assert assistant_response_found
        
        # Should have goodbye message
        goodbye_found = any("Goodbye!" in arg for arg in call_args)
        assert goodbye_found
    
    @patch('builtins.input', side_effect=["hello", "how are you", "bye", "/exit"])
    @patch('builtins.print')
    def test_full_integration_multiple_exchanges(self, mock_print, mock_input):
        """Test full integration with multiple message exchanges."""
        with patch('sys.argv', ['claude_code_mini.py', '--config', self.temp_config.name]):
            claude_code_mini.main()
        
        call_args = [str(call) for call in mock_print.call_args_list]
        
        # Count assistant responses (should be 3)
        assistant_responses = [arg for arg in call_args if "🤖 Assistant:" in arg]
        assert len(assistant_responses) == 3
    
    @patch('builtins.input', side_effect=["", "   ", "hello", "/exit"])
    @patch('builtins.print')
    def test_full_integration_empty_inputs(self, mock_print, mock_input):
        """Test full integration with empty inputs."""
        with patch('sys.argv', ['claude_code_mini.py', '--config', self.temp_config.name]):
            claude_code_mini.main()
        
        call_args = [str(call) for call in mock_print.call_args_list]
        
        # Should have system messages for empty inputs
        system_messages = [arg for arg in call_args if "💬 System:" in arg]
        assert len(system_messages) >= 2  # At least 2 empty input messages
        
        # Should have exactly 1 assistant response (for "hello")
        assistant_responses = [arg for arg in call_args if "🤖 Assistant:" in arg]
        assert len(assistant_responses) == 1
    
    @patch.dict(os.environ, {'KIMI_API_KEY': 'test-key-123'})
    @patch('builtins.input', side_effect=["/exit"])
    @patch('builtins.print')
    def test_full_integration_with_api_key(self, mock_print, mock_input):
        """Test full integration with API key from environment."""
        with patch('sys.argv', ['claude_code_mini.py', '--config', self.temp_config.name, '--verbose']):
            claude_code_mini.main()
        
        call_args = [str(call) for call in mock_print.call_args_list]
        
        # Should show API key is configured in verbose mode
        api_key_configured = any("API key configured: True" in arg for arg in call_args)
        assert api_key_configured
    
    @patch('builtins.input', side_effect=["/exit"])
    @patch('builtins.print')
    def test_full_integration_verbose_mode(self, mock_print, mock_input):
        """Test full integration in verbose mode."""
        with patch('sys.argv', ['claude_code_mini.py', '--config', self.temp_config.name, '--verbose']):
            claude_code_mini.main()
        
        call_args = [str(call) for call in mock_print.call_args_list]
        
        # Should have verbose CLI output
        config_loading = any("[CLI] Loading configuration from:" in arg for arg in call_args)
        model_info = any("[CLI] Model: test-model" in arg for arg in call_args)
        
        assert config_loading
        assert model_info