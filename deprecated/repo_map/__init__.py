"""
Minimalist Repository Map Implementation
========================================

A simplified replication of Aider's repository map functionality.
Provides intelligent code context generation within token budgets.

Core Components:
- RepoMap: Main class for repository analysis
- TagExtractor: Code parsing and tag extraction  
- SimpleRanker: Basic relevance ranking algorithm
- TreeFormatter: Output formatting and visualization

Usage:
    from repo_mat import RepoMap
    
    repo_map = RepoMap(root_dir=".", max_tokens=1000)
    context = repo_map.generate_map(chat_files=[], other_files=all_files)
    print(context)
"""

from .repo_map import RepoMap, Tag
from .tag_extractor import TagExtractor
from .ranking import SimpleRanker
from .tree_formatter import TreeFormatter

__version__ = "0.1.0"
__all__ = ["RepoMap", "Tag", "TagExtractor", "SimpleRanker", "TreeFormatter"]