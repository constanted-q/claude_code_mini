# Claude Code Mini

A minimalist Python implementation of Claude Code's core functionality, strategically borrowing from the best of Aider and Goose open-source projects.

## ✅ Current Features

**Working CLI Chatbot with Real LLM Integration:**
- Interactive command-line chat interface
- Real Kimi K2 model integration via Moonshot API
- Multi-turn conversation context memory
- Graceful fallback to mock responses when API unavailable
- Comprehensive error handling and verbose logging

**Integrated Tool System:**
- Tool registry with automatic discovery
- OpenAI function calling format support
- ReadTool for file reading with line-based navigation
- Tool execution in conversation flow with proper ordering
- Commands: `/tools` (list tools), `/toggle-tools` (enable/disable)

**Advanced Context Management:**
- Unified context format supporting future extensions
- Conversation history preservation across chat sessions
- Context filtering by type (conversation, repo, tool, system)
- Automatic context truncation to prevent token overflow

## 🏗️ Architecture

```
CLI (claude_code_mini.py)
    ↓
Session (session.py) - I/O, preprocessing, context management
    ↓  
Agent (agent.py) - Response generation, model selection
    ↓
Models (models.py) - LLM API integration (Kimi K2)
    ↓
Tools (tools/) - Tool registry and execution
```

### Key Components

- **Session**: Handles user I/O, input preprocessing, response postprocessing, and unified context management
- **Agent**: Orchestrates response generation, manages model clients, and handles API fallbacks
- **Models**: OpenAI SDK-based integration with Kimi K2 model via Moonshot API
- **Tools**: Registry system with auto-discovery, base Tool class, and ReadTool implementation
- **Unified Context**: Extensible format supporting conversation, repository, and tool contexts

## 🚀 Quick Start

### Installation

```bash
git clone <repository-url>
cd claude_code_mini
pip install -r requirements.txt
```

### Configuration

1. **Set API Key** (for real LLM responses):
   ```bash
   export MOONSHOT_API_KEY="your-kimi-api-key"
   ```

2. **Configure Model** (optional, defaults to Kimi K2):
   Edit `config.yml`:
   ```yaml
   model: kimi-k2-0711-preview
   base_url: https://api.moonshot.cn/v1
   max_tokens: 4096
   temperature: 0.2
   ```

### Usage

```bash
# Basic usage
python claude_code_mini.py

# Verbose mode
python claude_code_mini.py --verbose

# Custom config
python claude_code_mini.py --config my_config.yml
```

### Example Session

```
🤖 Welcome to Claude Code Mini!
Type your messages below. Use '/exit' to quit.
Type '/help' for available commands and '/tools' to list tools.
Tools available: read_file

🟢 You: Hello, my name is Alice
🤖 Assistant: Hello Alice! Nice to meet you. How can I help you today?

🟢 You: Can you read the config.yml file?
🤖 Assistant: I'll read the config.yml file for you.

🔧 Tool 'read_file' executed:
1	# Enhanced Claude Code Configuration
2	# Following Aider's config pattern
3	
4	# Model settings - Kimi K2 via Moonshot API
5	model: kimi-k2-0711-preview
...

🤖 Assistant: The config.yml file contains configuration settings for the Claude Code Mini application, including model settings for Kimi K2 and various agent parameters.

🟢 You: /tools
💬 System: Available Tools:

• read_file: Read text files with encoding detection
  Instructions: Use this tool to read and analyze file contents

🟢 You: /exit
👋 Goodbye! Session Summary:
   • Duration: 45 seconds
   • Messages exchanged: 3
   • Context entries: 8
```

## 🧪 Testing

Run the test suite:

```bash
# All tests
python -m pytest tests/ -v

# Specific components
python -m pytest tests/test_models.py -v
python -m pytest tests/test_agent.py -v
python -m pytest tests/test_session.py -v
```

## 🎯 Project Goals

This weekend project implements Claude Code's essential features:

1. ✅ **CLI Interface** - Command-line interaction with comprehensive options
2. 🚧 **Repository Context Gathering** - Smart codebase understanding 
3. ✅ **Agent Loop with Tool Execution** - Conversational AI with action capabilities
4. 🚧 **Sub-Agents** - Process-isolated parallel task execution
5. 🚧 **File Patching** - Unified diff-based code modifications

**Legend**: ✅ Complete | 🚧 Planned | ❌ Not Started

## 📋 Roadmap

### Phase 1: Foundation ✅ COMPLETE
- [x] Basic CLI interface with argument parsing
- [x] Session management with I/O handling
- [x] Agent architecture with model abstraction
- [x] Real LLM integration (Kimi K2)
- [x] Conversation context management
- [x] Unified context format for future extensibility
- [x] Comprehensive test coverage

### Phase 2: Repository Integration 🚧 NEXT
- [ ] Repository context gathering and analysis
- [ ] File content integration into context
- [ ] Code structure understanding
- [ ] Relevance-based context filtering

### Phase 3: Tool Execution ✅ COMPLETE
- [x] Tool registry and management with auto-discovery
- [x] Base Tool class with metadata and execution
- [x] ReadTool for file reading with line-based navigation
- [x] OpenAI function calling format support
- [x] Tool execution in conversation flow
- [ ] Git integration (future enhancement)

### Phase 4: Advanced Features 🚧 FUTURE
- [ ] Sub-agent architecture
- [ ] Parallel task execution
- [ ] File patching with unified diffs
- [ ] Web interface

## 🛠️ Dependencies

- **Python 3.8+**
- **pyyaml>=6.0** - Configuration management
- **openai>=1.0.0** - LLM API integration
- **pytest>=7.0.0** - Testing framework

## 🤝 Contributing

This is a learning project demonstrating Claude Code's core concepts. Feel free to explore the codebase and suggest improvements!

## 📄 License

Open source - feel free to use and modify.

---

**Inspired by**: [Aider](https://github.com/paul-gauthier/aider) (CLI design, repo context) | [Goose](https://github.com/square/goose) (agent architecture, conversation management)