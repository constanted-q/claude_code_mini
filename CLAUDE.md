# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a minimalist Python implementation of Claude Code that demonstrates core AI assistant functionality. It's a weekend project implementing Claude Code's essential features by strategically borrowing patterns from Aider and Goose:

**From Aider**: CLI design, repository context gathering, patch engine, coder abstractions
**From Goose**: Agent loop, tool execution system, sub-agent architecture, conversation management

## Current Implementation Status

### ✅ COMPLETED FEATURES

**Phase 1: Foundation (100% Complete)**
- **CLI Interface**: Full command-line interface with argument parsing (`claude_code_mini.py`)
- **Session Management**: Complete I/O handling, preprocessing, postprocessing (`session.py`)
- **Agent Architecture**: Model abstraction with fallback handling (`agent.py`) 
- **LLM Integration**: Real Kimi K2 model via Moonshot API (`models.py`)
- **Context Management**: Unified context format supporting future extensions
- **Testing**: Comprehensive test suite with 15 core tests

**Phase 3: Tool Execution (100% Complete)**
- **Tool Registry**: Auto-discovery and management system (`tools/__init__.py`)
- **Base Tool Class**: Abstract tool interface with metadata and execution (`tools/base_tool.py`)
- **ReadTool**: File reading with line-based navigation and cat -n formatting (`tools/read_tool.py`)
- **OpenAI Function Calling**: Full support for tool schemas and execution
- **Conversation Integration**: Tool calls and results properly ordered in message flow
- **Tool Commands**: `/tools` to list, `/toggle-tools` to enable/disable

### 🚧 PLANNED FEATURES

**Phase 2: Repository Integration (Next Priority)**
- Repository context gathering and code analysis
- File content integration into conversation context
- Code structure understanding and relevance filtering


**Phase 4: Advanced Features**
- Sub-agent architecture for parallel processing
- File patching with unified diffs
- Web interface

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

tools/ (Tool System)
├── __init__.py - Tool registry with auto-discovery
├── base_tool.py - Abstract Tool class with metadata
└── read_tool.py - File reading tool with line navigation
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
- **Repository Context**: Not yet implemented (Phase 2)
- **File Operations**: Limited to reading, no modification capabilities yet
- **Sub-Agents**: Planned for Phase 4
- **Git Integration**: Not yet available

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
- **Simplified Coverage**: Essential tests only, avoiding over-testing

## Future Development Roadmap

### Immediate Next Steps (Phase 2)
1. **Repository Scanner**: Analyze codebase structure and identify relevant files
2. **Context Relevance**: Score and filter repository content for inclusion
3. **File Integration**: Add file content to unified context format
4. **Smart Context**: Include only relevant code based on user queries

### Medium Term (Next Enhancements)
1. **File Operations**: Create, update, delete file capabilities (read already implemented)
2. **Code Execution**: Safe execution of code snippets and commands
3. **Git Integration**: Version control operations and diff management
4. **Additional Tools**: Write, Edit, Search, and Execute tools

### Long Term (Phase 4) 
1. **Sub-Agent Architecture**: Parallel task execution with process isolation
2. **Advanced Patching**: Unified diff-based code modifications
3. **Web Interface**: Browser-based interaction alternative to CLI
4. **Advanced Context**: Semantic code understanding and intelligent filtering

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