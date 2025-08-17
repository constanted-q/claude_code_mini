# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a minimalist Python implementation of Claude Code that demonstrates core AI assistant functionality. It's a weekend project implementing Claude Code's essential features with multi-agent orchestration and advanced tool execution capabilities.

## Current Implementation Status

### ✅ COMPLETED FEATURES

**Phase 1: Foundation (100% Complete)**
- **CLI Interface**: Full command-line interface with argument parsing (`claude_code_mini.py`)
- **Session Management**: Complete I/O handling, preprocessing, postprocessing (`session.py`)
- **Agent Architecture**: Model abstraction with fallback handling (`agent.py`) 
- **LLM Integration**: Real Kimi K2 model via Moonshot API (`models.py`)
- **Context Management**: Unified context format supporting future extensions
- **Testing**: Comprehensive test suite with 15 core tests

**Phase 2: Advanced Tool System (100% Complete)**
- **Tool Registry**: Auto-discovery and management system (`tools/__init__.py`)
- **Base Tool Class**: Abstract tool interface with metadata and execution (`tools/base_tool.py`)
- **ReadTool**: File reading with line-based navigation and cat -n formatting (`tools/read_tool.py`)
- **EditTool**: File editing with diff preview and user confirmation (`tools/edit_tool.py`)
- **GrepTool**: Pattern searching across files with regex support (`tools/grep_tool.py`)
- **GlobTool**: File pattern matching for discovery (`tools/glob_tool.py`)
- **AgentTool**: Sub-agent orchestration and task delegation (`tools/agent_tool.py`)
- **OpenAI Function Calling**: Full support for tool schemas and execution
- **Conversation Integration**: Tool calls and results properly ordered in message flow
- **Tool Commands**: `/tools` to list, `/toggle-tools` to enable/disable

**Phase 3: Sub-Agent Architecture (100% Complete)**
- **Dynamic Agent Creation**: `/agent -new` command for specialized sub-agent generation
- **Agent Configuration**: YAML-based agent configs with tool assignment (`sub_agents/`)
- **Task Delegation**: Multi-agent coordination via AgentTool
- **Specialized Agents**: Domain-specific agents (file-finder, lyric-writer, etc.)
- **Complex Workflows**: Multi-agent orchestration demonstrated in Write Lyric demo

### 🚧 PLANNED FEATURES

**Phase 4: Advanced Features**
- File patching with unified diffs
- Git integration and version control
- Web interface
- Advanced context intelligence

## Technical Architecture

### Core Components

```
claude_code_mini.py (CLI Entry Point)
├── Argument parsing and configuration loading
├── Dependency checking and error handling
└── Session initialization and execution

session.py (I/O and Context Management)
├── Interactive chat loop with user input/output
├── Input preprocessing and response postprocessing  
├── Unified context management with type filtering
└── Session statistics and context truncation

agent.py (Response Generation)
├── Model client initialization and management
├── Response generation with real LLM or mock fallback
├── Configuration management with YAML support
└── Error handling and verbose logging

models.py (LLM API Integration)
├── Kimi K2 integration via OpenAI SDK
├── Context format conversion (unified → OpenAI messages)
├── API error handling with graceful fallback
└── Tool result ordering and validation

sub_agent.py (Sub-Agent Management)
├── Dynamic agent creation and configuration
├── Agent-to-agent communication
├── Task delegation and coordination
└── YAML-based agent persistence

tools/ (Tool System)
├── __init__.py - Tool registry with auto-discovery
├── base_tool.py - Abstract Tool class with metadata
├── read_tool.py - File reading tool with line navigation
├── edit_tool.py - File editing with diff preview
├── grep_tool.py - Pattern searching across files
├── glob_tool.py - File pattern matching
└── agent_tool.py - Sub-agent orchestration
```

### Unified Context Format

**Design Philosophy**: Extensible context management supporting multiple context types (conversation, repository, tool, system) with consistent structure.

**Format Specification**:
```python
{
    "type": "conversation" | "repo" | "tool" | "system",
    "role": "user" | "assistant" | "system" | "tool",
    "content": "message/data content",
    "metadata": {
        "timestamp": "ISO format",
        "message_id": "unique_identifier",
        # Type-specific fields...
    }
}
```

**Context Type Examples**:

*Conversation Context*:
```python
{
    "type": "conversation",
    "role": "user",
    "content": "Hello, my name is Alice",
    "metadata": {"timestamp": "2024-01-01T12:00:00", "message_id": "1_user"}
}
```

*Repository Context (Future)*:
```python
{
    "type": "repo", 
    "role": "system",
    "content": "def calculate_sum(a, b): return a + b",
    "metadata": {"file_path": "utils.py", "line_range": "10-12", "relevance": 0.8}
}
```

*Tool Context (Implemented)*:
```python
{
    "type": "tool",
    "role": "tool", 
    "content": "File content here...",
    "metadata": {
        "tool_name": "read_file",
        "tool_call_id": "call_abc123",
        "execution_time": 0.5,
        "success": true
    }
}
```

## Development Guidelines

### Code Standards
- **No Comments**: Code should be self-documenting unless explicitly needed
- **Minimal Dependencies**: Only essential packages (pyyaml, openai, pytest)
- **Error Handling**: Graceful fallbacks for all external dependencies
- **Testing**: Simple, focused tests covering core functionality

### Configuration Management
- **Environment Variables**: Use `MOONSHOT_API_KEY` for API access
- **YAML Configuration**: `config.yml` for model and generation settings
- **Defaults**: Sensible fallbacks for all configuration options

### Model Integration
- **Primary Model**: Kimi K2 (`kimi-k2-0711-preview`) via Moonshot API
- **Base URL**: `https://api.moonshot.cn/v1`
- **OpenAI SDK**: Standard OpenAI client for consistent API interface
- **Fallback**: Mock responses when API unavailable or misconfigured

### Context Management Strategy
- **Conversation Context**: Automatically managed by session
- **Context Filtering**: By type to include relevant context only
- **Token Management**: Automatic truncation to prevent overflow (20 messages = 10 exchanges)
- **Future Extensions**: Ready for repo context integration

## Implementation Notes

### Current Limitations
- **Git Integration**: Not yet available
- **File Patching**: Unified diff system not implemented
- **Web Interface**: CLI-only interaction currently
- **Advanced Context**: Repository intelligence not implemented

### Key Design Decisions
- **Unified Context Format**: Enables seamless integration of different context types
- **OpenAI SDK**: Provides standard interface for multiple LLM providers
- **Session-Agent Separation**: Clean architecture for I/O vs. logic separation
- **Mock Fallbacks**: Ensures functionality without external dependencies

### Testing Strategy
- **Unit Tests**: Core functionality with mocked dependencies
- **Integration Tests**: End-to-end workflow validation
- **Context Tests**: Unified format handling and filtering
- **Tool Tests**: Registry, execution, and OpenAI format (test_tools.py, test_fixes.py)
- **Multi-Agent Tests**: Sub-agent creation and coordination
- **Demo Validation**: Write Lyric demo showcases full system capabilities
- **Simplified Coverage**: Essential tests only, avoiding over-testing

## Future Development Roadmap

### Immediate Next Steps (Phase 4)
1. **File Patching**: Unified diff-based code modifications
2. **Git Integration**: Version control operations and diff management  
3. **Code Execution**: Safe execution of code snippets and commands
4. **Web Interface**: Browser-based interaction alternative to CLI

### Medium Term (Advanced Features)
1. **Repository Intelligence**: Smart codebase understanding and context
2. **Advanced Context**: Semantic code understanding and intelligent filtering
3. **Process Isolation**: Enhanced sub-agent security and performance
4. **Workflow Templates**: Pre-built multi-agent workflows for common tasks

### Long Term (Vision)
1. **Multi-Repository**: Cross-project context and operations
2. **Cloud Integration**: Remote execution and collaboration
3. **Plugin System**: Third-party tool and agent extensions
4. **Visual Interface**: Graph-based workflow visualization

---

## Important Instructions for Claude Code

When working with this codebase:

1. **NEVER create files unless absolutely necessary** - Always prefer editing existing files
2. **Follow the unified context format** when adding new context types
3. **Maintain backwards compatibility** when extending the architecture
4. **Keep tests simple and focused** - Avoid over-testing
5. **Use the existing error handling patterns** for new integrations
6. **Preserve the mock fallback capability** for all external dependencies

The codebase is designed for extensibility while maintaining simplicity. Any new features should follow the established patterns and architectural decisions.
- Never run pip install command, leave it to the user.
- Don't write tests or execute tests unless the user asked explicitly.