#!/usr/bin/env python3
"""
Claude Code Mini - A simple CLI chatbot implementation.

This is a minimalist Python implementation of Claude Code that demonstrates 
core AI assistant functionality. It implements essential features by 
strategically borrowing patterns from Aider and Goose.
"""

import argparse
import sys
import os
from pathlib import Path

from agent import Agent
from session import Session


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Claude Code Mini - Simple CLI Chatbot",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--config",
        "-c",
        default="config.yml",
        help="Path to configuration file (default: config.yml)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Claude Code Mini v0.1.0"
    )
    
    return parser.parse_args()


def check_dependencies():
    """Check if required dependencies are available."""
    try:
        import yaml
    except ImportError:
        print("❌ Error: PyYAML is required but not installed.")
        print("Please install it with: pip install pyyaml")
        sys.exit(1)


def main():
    """Main entry point for the CLI application."""
    args = parse_arguments()
    
    # Check dependencies
    check_dependencies()
    
    # Print header
    if not args.verbose:
        print("Claude Code Mini v0.1.0")
        print("Type '/exit' to quit\n")
    
    try:
        # Initialize agent with configuration
        if args.verbose:
            print(f"[CLI] Loading configuration from: {args.config}")
        
        agent = Agent(config_path=args.config)
        
        if args.verbose:
            model_info = agent.get_model_info()
            print(f"[CLI] Model: {model_info['model']}")
            print(f"[CLI] Max tokens: {model_info['max_tokens']}")
            print(f"[CLI] Temperature: {model_info['temperature']}")
            print(f"[CLI] API key configured: {model_info['has_api_key']}")
        
        # Initialize session
        session = Session(agent, verbose=args.verbose)
        
        # Start interactive chat session
        session.start_session()
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        if args.verbose:
            print(f"❌ Fatal error: {str(e)}")
            import traceback
            traceback.print_exc()
        else:
            print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()