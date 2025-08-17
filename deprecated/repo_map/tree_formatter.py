"""
Tree Formatting Component
=========================

Formats the repository map as a hierarchical tree structure.
Provides clean, readable output similar to Aider's tree representation.
"""

from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Set, Tuple

try:
    from .repo_map import Tag
except ImportError:
    from repo_map import Tag


class TreeFormatter:
    """
    Formats repository information as a tree structure.
    
    Creates clean, hierarchical representations of code structure
    that are easy for LLMs to understand and process.
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def format_tree(
        self,
        ranked_files: List[Tuple[str, float]],
        tags_by_file: Dict[str, List[Tag]],
        chat_files: Set[str]
    ) -> str:
        """
        Format files as a tree structure.
        
        Args:
            ranked_files: List of (filename, score) tuples in relevance order
            tags_by_file: Tags for each file
            chat_files: Files currently in chat (to be excluded from output)
            
        Returns:
            Formatted tree string
        """
        if not ranked_files:
            return ""
        
        output_lines = []
        
        for filepath, score in ranked_files:
            # Skip chat files in the output
            if any(cf in filepath for cf in chat_files):
                continue
                
            tags = tags_by_file.get(filepath, [])
            
            # Format this file's section
            file_section = self._format_file_section(filepath, tags, score)
            if file_section:
                output_lines.append(file_section)
        
        return "\n".join(output_lines)
    
    def _format_file_section(self, filepath: str, tags: List[Tag], score: float) -> str:
        """Format a single file's section."""
        lines = []
        
        # File header
        filename = Path(filepath).name
        if self.verbose:
            lines.append(f"\n{filepath} (score: {score:.2f}):")
        else:
            lines.append(f"\n{filepath}:")
        
        # Group tags by type and line number
        definitions = []
        references_by_line = defaultdict(list)
        
        for tag in tags:
            if tag.kind == 'def':
                definitions.append(tag)
            elif tag.kind == 'ref':
                references_by_line[tag.line].append(tag)
        
        # Sort definitions by line number
        definitions.sort(key=lambda t: t.line)
        
        # Check if we should show detailed structure or just file listing
        if self._should_show_detailed_structure(filepath, definitions):
            lines.extend(self._format_detailed_structure(definitions))
        else:
            # Just show the file name for simple files
            pass
        
        return "\n".join(lines)
    
    def _should_show_detailed_structure(self, filepath: str, definitions: List[Tag]) -> bool:
        """Determine if we should show detailed structure for this file."""
        path = Path(filepath)
        
        # Always show structure for code files with definitions
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.cpp', '.c', '.h'}
        if path.suffix.lower() in code_extensions and definitions:
            return True
        
        # Don't show structure for config files, docs, etc.
        return False
    
    def _format_detailed_structure(self, definitions: List[Tag]) -> List[str]:
        """Format detailed structure for a file with definitions."""
        lines = []
        
        # Group definitions by type (based on naming conventions)
        classes = []
        functions = []
        variables = []
        
        for tag in definitions:
            if self._looks_like_class(tag.name):
                classes.append(tag)
            elif self._looks_like_function(tag.name, tag.line):
                functions.append(tag)
            else:
                variables.append(tag)
        
        # Format classes first
        for cls_tag in classes:
            lines.append(f"├── class {cls_tag.name}")
        
        # Then functions
        for func_tag in functions:
            lines.append(f"├── def {func_tag.name}()")
        
        # Finally variables/constants
        for var_tag in variables:
            if var_tag.name.isupper():
                lines.append(f"├── const {var_tag.name}")
            else:
                lines.append(f"├── var {var_tag.name}")
        
        return lines
    
    def _looks_like_class(self, name: str) -> bool:
        """Heuristic to determine if name looks like a class."""
        # Classes typically start with uppercase
        return name and name[0].isupper() and '_' not in name
    
    def _looks_like_function(self, name: str, line: int) -> bool:
        """Heuristic to determine if name looks like a function."""
        # Functions typically are lowercase or snake_case
        # This is a simplified heuristic
        return name and (name.islower() or '_' in name) and not name.isupper()
    
    def format_summary(self, repo_map: str, stats: Dict) -> str:
        """Format a summary of the repository map."""
        lines = []
        
        if self.verbose and stats:
            lines.append("Repository Map Summary")
            lines.append("=" * 20)
            lines.append(f"Processing time: {stats.get('last_processing_time', 0):.2f}s")
            lines.append(f"Cache entries: {stats.get('cache_size', 0)}")
            lines.append(f"Root directory: {stats.get('root_directory', 'Unknown')}")
            lines.append("")
        
        lines.append(repo_map)
        
        return "\n".join(lines)
    
    def format_compact(self, ranked_files: List[Tuple[str, float]], max_files: int = 10) -> str:
        """Format a compact listing of top files."""
        lines = ["Top repository files:"]
        
        for i, (filepath, score) in enumerate(ranked_files[:max_files]):
            filename = Path(filepath).name
            if self.verbose:
                lines.append(f"{i+1:2d}. {filename} (score: {score:.2f})")
            else:
                lines.append(f"{i+1:2d}. {filename}")
        
        return "\n".join(lines)
    
    def format_file_tree(self, filepaths: List[str]) -> str:
        """Format files as a directory tree structure."""
        if not filepaths:
            return ""
        
        # Build tree structure
        tree = {}
        for filepath in filepaths:
            parts = Path(filepath).parts
            current = tree
            for part in parts[:-1]:  # Directories
                if part not in current:
                    current[part] = {}
                current = current[part]
            # Add file
            current[parts[-1]] = None
        
        # Format tree
        return self._format_tree_recursive(tree, prefix="")
    
    def _format_tree_recursive(self, tree: Dict, prefix: str = "", is_last: bool = True) -> str:
        """Recursively format tree structure."""
        lines = []
        items = sorted(tree.items())
        
        for i, (name, subtree) in enumerate(items):
            is_last_item = i == len(items) - 1
            current_prefix = "└── " if is_last_item else "├── "
            lines.append(f"{prefix}{current_prefix}{name}")
            
            if subtree is not None:  # Directory
                extension = "    " if is_last_item else "│   "
                sublines = self._format_tree_recursive(
                    subtree, 
                    prefix + extension, 
                    is_last_item
                )
                lines.append(sublines)
        
        return "\n".join(lines)
    
    def truncate_long_lines(self, text: str, max_length: int = 100) -> str:
        """Truncate long lines to prevent overwhelming output."""
        lines = text.splitlines()
        truncated_lines = []
        
        for line in lines:
            if len(line) > max_length:
                truncated_lines.append(line[:max_length] + "...")
            else:
                truncated_lines.append(line)
        
        return "\n".join(truncated_lines)