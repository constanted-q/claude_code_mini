# Repository Map - Minimalist Implementation

A simplified replication of Aider's repository map functionality, providing intelligent code context generation for Large Language Models within token budgets.

## Overview

This implementation captures the core functionality of Aider's sophisticated repository mapping system while being more approachable and easier to understand. It analyzes codebases to generate hierarchical summaries that maximize relevance while fitting within LLM context windows.

## Key Features

- **Multi-language Support**: Python (AST-based), JavaScript, TypeScript, Go, Rust, Java, C/C++
- **Intelligent Ranking**: Reference-based scoring with importance weighting
- **Token Budget Management**: Binary search optimization for context window constraints
- **Multi-level Caching**: File, tag, and result caching for performance
- **Context Awareness**: Boosts relevance for mentioned files and identifiers
- **Clean Tree Output**: Hierarchical representation similar to Aider's format

## Architecture

```
repo_mat/
├── __init__.py          # Package initialization
├── repo_map.py          # Main RepoMap class
├── tag_extractor.py     # Code analysis and tag extraction
├── ranking.py           # File relevance ranking algorithm
├── tree_formatter.py    # Output formatting
├── demo.py              # Demonstration script
└── README.md            # This file
```

## Core Components

### 1. RepoMap (Main Controller)
- Orchestrates the entire analysis pipeline
- Manages token budgets and caching
- Provides the main API interface

### 2. TagExtractor (Code Analysis)
- Extracts definitions and references from source files
- Uses Python AST for Python files
- Regex patterns for other languages

### 3. SimpleRanker (Relevance Scoring)
- Simplified alternative to Aider's PageRank algorithm
- Scores files based on references, importance, and mentions
- Handles chat context and identifier matching

### 4. TreeFormatter (Output Generation)  
- Formats analysis results as hierarchical trees
- Creates clean, LLM-friendly representations
- Handles file structure visualization

## Usage

### Basic Usage

```python
from repo_mat import RepoMap

# Initialize with token budget
repo_map = RepoMap(root_dir=".", max_tokens=1024, verbose=True)

# Generate repository map
context = repo_map.generate_map()
print(context)
```

### Advanced Usage

```python
# With specific files and mentions
context = repo_map.generate_map(
    chat_files=["src/main.py", "tests/test_main.py"],
    mentioned_files={"README.md", "config.py"},
    mentioned_idents={"DatabaseManager", "process_data"},
    force_refresh=True  # Bypass cache
)
```

### Command Line Interface

```bash
# Basic analysis
python demo.py

# Analyze specific directory
python demo.py /path/to/project --max-tokens 2048 --verbose

# With context
python demo.py . --chat-files main.py --mentioned DatabaseManager config.py

# Force refresh and show stats
python demo.py --refresh --stats
```

## Comparison with Aider's Implementation

| Feature | Aider's Implementation | This Implementation |
|---------|----------------------|-------------------|
| **Parsing** | Tree-sitter (comprehensive) | AST + Regex (simplified) |
| **Ranking** | PageRank (graph-based) | Reference counting + scoring |
| **Caching** | SQLite + memory (robust) | Memory only (simple) |
| **Languages** | 50+ languages | 8 major languages |
| **Token Counting** | Model-specific tokenizers | Character-based estimation |
| **Error Handling** | Production-grade | Basic |
| **Performance** | Optimized for large repos | Good for medium repos |

## Example Output

```
src/database.py:
├── class DatabaseManager
├── def connect()
├── def execute_query()
├── def close_connection()

src/main.py:
├── def main()
├── def process_arguments()
├── var config

tests/test_database.py:
├── class TestDatabaseManager
├── def test_connection()

requirements.txt
README.md
```

## Key Insights from Aider's Design

### 1. **Graph-Theoretic Approach**
Aider uses PageRank to model code relationships as a graph where files are nodes and references are edges. This captures indirect relationships and code importance.

**Our Simplification**: Direct scoring based on reference counts and patterns, which captures most practical relevance without graph complexity.

### 2. **Context-Aware Personalization**
Aider's PageRank uses personalization vectors to bias ranking toward chat files and mentioned identifiers.

**Our Implementation**: Direct scoring boosts for mentioned files/identifiers and chat context.

### 3. **Token Budget Optimization**
Binary search to find optimal content within strict token limits.

**Our Implementation**: Same binary search approach - this is a key algorithmic insight worth preserving.

### 4. **Multi-Level Caching**
Sophisticated caching with graceful degradation for performance.

**Our Simplification**: Memory-only caching, sufficient for development use.

### 5. **Tree-Sitter Integration**
Language-specific parsing for accurate code understanding.

**Our Approach**: Python AST (accurate) + regex patterns (practical for other languages).

## Performance Characteristics

### Time Complexity
- **File Discovery**: O(n) where n = number of files
- **Tag Extraction**: O(n×f) where f = average file size  
- **Ranking**: O(t×f) where t = total tags, f = files
- **Tree Generation**: O(log(t) × token_estimation_time)

### Space Complexity
- **Memory Usage**: O(files × avg_file_size) for caching
- **Output Size**: Bounded by max_tokens parameter

### Recommended Usage
- **Small to Medium Projects**: < 10k files, works well
- **Large Projects**: May need optimization or use Aider directly
- **Development/Learning**: Excellent for understanding concepts

## Advanced Features

### Custom Ranking Weights

```python
class CustomRanker(SimpleRanker):
    def _get_importance_boost(self, filepath):
        # Custom logic for your project structure
        if 'critical' in filepath:
            return 10.0
        return super()._get_importance_boost(filepath)

repo_map = RepoMap(...)
repo_map.ranker = CustomRanker()
```

### Language-Specific Patterns

```python
# Add support for new language
tag_extractor.rust_patterns = {
    'def': [r'^\s*pub fn (\w+)', r'^\s*struct (\w+)'],
    'ref': r'\b([a-zA-Z_]\w*)\b'
}
```

## Limitations

1. **Parsing Accuracy**: Regex-based parsing less accurate than tree-sitter
2. **Language Coverage**: Limited compared to Aider's comprehensive support
3. **Scalability**: Memory-only caching limits scalability
4. **Token Estimation**: Character-based approximation vs. real tokenizers
5. **Error Handling**: Basic error recovery compared to production system

## Future Enhancements

1. **Tree-sitter Integration**: For production accuracy
2. **Persistent Caching**: SQLite or file-based caching
3. **Model-Specific Tokenizers**: Real token counting
4. **Language Plugin System**: Extensible language support
5. **Configuration System**: User-customizable ranking weights

## Educational Value

This implementation serves as:
- **Learning Tool**: Understand Aider's core concepts
- **Research Base**: Experiment with ranking algorithms  
- **Integration Example**: Show how to build similar systems
- **Performance Baseline**: Compare different approaches

## Installation

No external dependencies required for basic functionality:

```python
# Just copy the repo_mat folder to your project
import sys
sys.path.append('/path/to/repo_mat')
from repo_mat import RepoMap
```

Optional dependencies for enhanced functionality:
```bash
pip install pathlib  # Usually included in Python 3.4+
```

## Testing

```python
# Run demo scenarios
python demo.py

# Test on different project types
python demo.py /path/to/python/project --verbose
python demo.py /path/to/javascript/project --max-tokens 500

# Compare with different settings
python demo.py . --mentioned MyClass DatabaseManager --stats
```

## Contributing

This is a educational/research implementation. Key areas for improvement:

1. **Parser Enhancement**: Add tree-sitter support
2. **Language Support**: Add more language patterns
3. **Ranking Algorithms**: Experiment with different scoring approaches
4. **Performance**: Optimize for larger codebases
5. **Testing**: Add comprehensive test suite

## License

MIT License - Feel free to use, modify, and learn from this code.

## Acknowledgments

This implementation is inspired by Aider's sophisticated repository mapping system. The core insights and architectural patterns come from analyzing Aider's production-grade implementation at https://github.com/paul-gauthier/aider.

The goal is to make these concepts accessible for learning and experimentation while preserving the essential intelligence of the original system.