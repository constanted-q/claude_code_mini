"""
Core Repository Map Implementation
==================================

Minimalist replication of Aider's repository mapping functionality.
Provides intelligent code context generation with token budget management.
"""

import os
import time
from collections import namedtuple, defaultdict
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple

# Core data structure for code elements
Tag = namedtuple("Tag", ["rel_fname", "fname", "line", "name", "kind"])


class RepoMap:
    """
    Minimalist repository map generator.
    
    Analyzes codebases to generate intelligent summaries that fit within
    token budgets while maximizing relevance for code understanding.
    """
    
    # Important files that should be prioritized
    IMPORTANT_FILES = {
        # Documentation
        "README.md", "README.txt", "README.rst", "README",
        "CONTRIBUTING.md", "LICENSE", "CHANGELOG.md",
        
        # Configuration
        "requirements.txt", "package.json", "Cargo.toml", "pyproject.toml",
        ".gitignore", ".env", "setup.py", "Makefile",
        
        # Build and testing
        "pytest.ini", "tox.ini", "jest.config.js", "webpack.config.js"
    }
    
    # Supported file extensions for analysis
    SUPPORTED_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".cpp", 
        ".c", ".h", ".hpp", ".cs", ".php", ".rb", ".swift", ".kt", ".scala"
    }
    
    def __init__(
        self, 
        root_dir: str = ".", 
        max_tokens: int = 1024,
        multiplier_no_files: float = 2.0,
        verbose: bool = False
    ):
        """
        Initialize repository map generator.
        
        Args:
            root_dir: Root directory to analyze
            max_tokens: Maximum tokens for output  
            multiplier_no_files: Token multiplier when no chat files
            verbose: Enable verbose output
        """
        self.root = Path(root_dir).resolve()
        self.max_tokens = max_tokens
        self.multiplier_no_files = multiplier_no_files
        self.verbose = verbose
        
        # Caches
        self._file_cache = {}  # File content cache
        self._tag_cache = {}   # Tag extraction cache
        self._map_cache = {}   # Generated map cache
        
        # Statistics
        self.last_processing_time = 0.0
        
        # Initialize components
        try:
            from .tag_extractor import TagExtractor
            from .ranking import SimpleRanker
            from .tree_formatter import TreeFormatter
        except ImportError:
            from tag_extractor import TagExtractor
            from ranking import SimpleRanker
            from tree_formatter import TreeFormatter
        
        self.tag_extractor = TagExtractor(self.root, verbose=verbose)
        self.ranker = SimpleRanker(verbose=verbose)
        self.formatter = TreeFormatter(verbose=verbose)
        
    def generate_map(
        self,
        chat_files: List[str] = None,
        other_files: List[str] = None,
        mentioned_files: Set[str] = None,
        mentioned_idents: Set[str] = None,
        force_refresh: bool = False
    ) -> str:
        """
        Generate repository map within token budget.
        
        Args:
            chat_files: Files currently in chat context
            other_files: Other repository files to consider
            mentioned_files: Files mentioned in conversation
            mentioned_idents: Identifiers mentioned in conversation
            force_refresh: Force regeneration, bypass cache
            
        Returns:
            Formatted repository map string
        """
        if chat_files is None:
            chat_files = []
        if other_files is None:
            other_files = self._discover_files()
        if mentioned_files is None:
            mentioned_files = set()
        if mentioned_idents is None:
            mentioned_idents = set()
            
        start_time = time.time()
        
        # Create cache key
        cache_key = self._create_cache_key(
            chat_files, other_files, mentioned_files, mentioned_idents
        )
        
        # Check cache unless force refresh
        if not force_refresh and cache_key in self._map_cache:
            if self.verbose:
                print("Using cached repository map")
            return self._map_cache[cache_key]
        
        # Adjust token budget based on chat files
        max_tokens = self.max_tokens
        if not chat_files:
            max_tokens = int(max_tokens * self.multiplier_no_files)
        
        if self.verbose:
            print(f"Generating repository map (max_tokens: {max_tokens})")
            print(f"Chat files: {len(chat_files)}, Other files: {len(other_files)}")
        
        # Extract tags from all files
        all_files = set(chat_files + other_files)
        tags_by_file = self._extract_tags_batch(all_files)
        
        # Rank files by relevance
        ranked_files = self.ranker.rank_files(
            tags_by_file,
            chat_files,
            mentioned_files,
            mentioned_idents
        )
        
        # Generate tree representation within token budget
        repo_map = self._generate_tree_within_budget(
            ranked_files, tags_by_file, max_tokens, set(chat_files)
        )
        
        self.last_processing_time = time.time() - start_time
        
        if self.verbose:
            print(f"Repository map generated in {self.last_processing_time:.2f}s")
            token_count = self._estimate_tokens(repo_map)
            print(f"Output tokens: {token_count}/{max_tokens}")
        
        # Cache result
        self._map_cache[cache_key] = repo_map
        
        return repo_map
    
    def _discover_files(self) -> List[str]:
        """Discover all relevant files in repository."""
        files = []
        
        for root, dirs, filenames in os.walk(self.root):
            # Skip common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for filename in filenames:
                filepath = Path(root) / filename
                rel_path = os.path.relpath(filepath, self.root)
                
                # Check if file should be included
                if self._should_include_file(filepath, filename):
                    files.append(str(filepath))
        
        # Sort by priority (important files first)
        files.sort(key=lambda f: (
            Path(f).name not in self.IMPORTANT_FILES,
            f
        ))
        
        return files
    
    def _should_include_file(self, filepath: Path, filename: str) -> bool:
        """Check if file should be included in analysis."""
        # Always include important files
        if filename in self.IMPORTANT_FILES:
            return True
            
        # Include files with supported extensions
        if filepath.suffix.lower() in self.SUPPORTED_EXTENSIONS:
            return True
            
        # Skip binary files, generated files, etc.
        skip_patterns = {'.git', '__pycache__', '.pytest_cache', 'node_modules',
                        '.venv', 'venv', '.tox', 'dist', 'build'}
        
        for part in filepath.parts:
            if part in skip_patterns:
                return False
                
        return False
    
    def _extract_tags_batch(self, files: Set[str]) -> Dict[str, List[Tag]]:
        """Extract tags from multiple files with caching."""
        tags_by_file = {}
        
        for filepath in files:
            rel_path = os.path.relpath(filepath, self.root)
            
            # Check cache first
            mtime = self._get_mtime(filepath)
            cache_key = (filepath, mtime)
            
            if cache_key in self._tag_cache:
                tags_by_file[rel_path] = self._tag_cache[cache_key]
                continue
                
            # Extract tags for this file
            tags = self.tag_extractor.extract_tags(filepath, rel_path)
            tags_by_file[rel_path] = tags
            
            # Cache result
            self._tag_cache[cache_key] = tags
        
        return tags_by_file
    
    def _generate_tree_within_budget(
        self, 
        ranked_files: List[Tuple[str, float]], 
        tags_by_file: Dict[str, List[Tag]],
        max_tokens: int,
        chat_files: Set[str]
    ) -> str:
        """Generate tree representation within token budget using binary search."""
        if not ranked_files:
            return ""
            
        # Binary search for optimal number of files
        low, high = 0, len(ranked_files)
        best_tree = ""
        best_tokens = 0
        
        while low <= high:
            mid = (low + high) // 2
            subset_files = ranked_files[:mid] if mid > 0 else []
            
            # Generate tree for this subset
            tree = self.formatter.format_tree(subset_files, tags_by_file, chat_files)
            token_count = self._estimate_tokens(tree)
            
            if token_count <= max_tokens:
                # This fits, try to include more
                if token_count > best_tokens:
                    best_tree = tree
                    best_tokens = token_count
                low = mid + 1
            else:
                # Too big, try fewer files
                high = mid - 1
        
        return best_tree
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (simplified)."""
        # Rough approximation: 1 token ≈ 4 characters on average
        # This is a simplification - real tokenizers are more complex
        return len(text) // 4
    
    def _get_mtime(self, filepath: str) -> float:
        """Get file modification time."""
        try:
            return os.path.getmtime(filepath)
        except OSError:
            return 0.0
    
    def _create_cache_key(
        self, 
        chat_files: List[str], 
        other_files: List[str],
        mentioned_files: Set[str], 
        mentioned_idents: Set[str]
    ) -> str:
        """Create cache key for the given parameters."""
        return str((
            tuple(sorted(chat_files)),
            tuple(sorted(other_files)),
            tuple(sorted(mentioned_files)), 
            tuple(sorted(mentioned_idents)),
            self.max_tokens
        ))
    
    def get_stats(self) -> Dict:
        """Get statistics about the repository map."""
        return {
            "cache_size": len(self._map_cache),
            "tag_cache_size": len(self._tag_cache),
            "last_processing_time": self.last_processing_time,
            "root_directory": str(self.root)
        }