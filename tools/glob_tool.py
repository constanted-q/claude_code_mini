"""
GlobTool implementation for finding files matching glob patterns.
"""

import os
import glob
from pathlib import Path
from typing import Dict, Any, List, Tuple
from .base_tool import Tool, ToolExecutionResult


class GlobTool(Tool):
    """Tool for finding files matching glob patterns in a directory."""
    
    @classmethod
    def get_name(cls) -> str:
        return "glob"
    
    @classmethod
    def get_description(cls) -> str:
        return "Find files matching glob patterns in a source directory"
    
    @classmethod
    def get_instructions(cls) -> str:
        return ("Use this tool to find files by pattern. Supports standard glob patterns like "
                "*.py (all Python files), **/*.js (JavaScript files recursively), "
                "src/**/*.ts (TypeScript files in src and subdirectories). "
                "Returns absolute file paths sorted by modification time (newest first).")
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match files (e.g., '*.py', '**/*.js', 'src/**/*.ts')"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (defaults to current working directory)",
                    "default": "."
                }
            },
            "required": ["pattern"]
        }
    
    def execute(self, tool_context=None, **kwargs) -> ToolExecutionResult:
        """
        Execute the glob file search operation.
        
        Args:
            tool_context: ToolContext (not used but kept for compatibility)
            pattern: Glob pattern to match files
            path: Directory to search in (optional, defaults to cwd)
            
        Returns:
            ToolExecutionResult with list of matching file paths and metadata
        """
        pattern = kwargs.get("pattern")
        search_path = kwargs.get("path", ".")
        
        if not pattern or not pattern.strip():
            return ToolExecutionResult(
                content="",
                success=False,
                error="Pattern cannot be empty"
            )
        
        try:
            # Resolve and validate search path
            base_path = Path(search_path).resolve()
            
            # Security check: ensure path is safe
            if not self._is_safe_path(str(base_path)):
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error="Access denied: path outside allowed directories"
                )
            
            # Check if base path exists
            if not base_path.exists():
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error=f"Search path does not exist: {search_path}"
                )
            
            # Check if it's a directory
            if not base_path.is_dir():
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error=f"Search path is not a directory: {search_path}"
                )
            
            # Find matching files
            matching_files = self._find_matching_files(pattern, base_path)
            
            # Sort by modification time (newest first)
            sorted_files = self._sort_by_modification_time(matching_files)
            
            # Convert to absolute paths and format output
            absolute_paths = [str(Path(f).resolve()) for f in sorted_files]
            
            # Create content output
            if not absolute_paths:
                content = f"No files found matching pattern '{pattern}' in '{search_path}'"
            else:
                content = "\n".join(absolute_paths)
            
            # Prepare metadata
            metadata = {
                "pattern": pattern,
                "search_path": str(base_path),
                "file_count": len(absolute_paths),
                "files": absolute_paths
            }
            
            return ToolExecutionResult(
                content=content,
                success=True,
                metadata=metadata
            )
            
        except Exception as e:
            return ToolExecutionResult(
                content="",
                success=False,
                error=f"Error during glob search: {str(e)}"
            )
    
    def _find_matching_files(self, pattern: str, base_path: Path) -> List[str]:
        """
        Find files matching the glob pattern.
        
        Args:
            pattern: Glob pattern to match
            base_path: Base directory to search in
            
        Returns:
            List of matching file paths
        """
        matching_files = []
        
        # Change to the base directory for glob operation
        original_cwd = os.getcwd()
        
        try:
            os.chdir(base_path)
            
            # Use glob with recursive support
            if "**" in pattern:
                # Recursive glob
                matches = glob.glob(pattern, recursive=True)
            else:
                # Regular glob
                matches = glob.glob(pattern)
            
            # Filter to only include files (not directories)
            for match in matches:
                match_path = Path(base_path) / match
                if match_path.is_file():
                    matching_files.append(str(match_path))
            
        finally:
            # Always restore original working directory
            os.chdir(original_cwd)
        
        return matching_files
    
    def _sort_by_modification_time(self, file_paths: List[str]) -> List[str]:
        """
        Sort files by modification time (newest first).
        
        Args:
            file_paths: List of file paths to sort
            
        Returns:
            Sorted list of file paths
        """
        def get_modification_time(file_path: str) -> float:
            try:
                return os.path.getmtime(file_path)
            except (OSError, IOError):
                # If we can't get modification time, use 0
                return 0.0
        
        # Sort by modification time, newest first (reverse=True)
        return sorted(file_paths, key=get_modification_time, reverse=True)
    
    def _is_safe_path(self, path: str) -> bool:
        """
        Check if the path is safe (no path traversal beyond allowed directories).
        
        Args:
            path: Path to check
            
        Returns:
            True if path is safe, False otherwise
        """
        try:
            # Get absolute path
            abs_path = os.path.abspath(path)
            
            # Get current working directory
            cwd = os.getcwd()
            
            # Check if the path is within current directory tree
            # This allows searching in subdirectories but not parent directories
            return abs_path.startswith(cwd)
            
        except Exception:
            return False
    
    def post_process(self, result: ToolExecutionResult) -> ToolExecutionResult:
        """
        Post-process the glob search result.
        
        Args:
            result: Raw execution result
            
        Returns:
            Processed result with additional formatting
        """
        if not result.success or not result.metadata:
            return result
        
        file_count = result.metadata.get("file_count", 0)
        pattern = result.metadata.get("pattern", "")
        search_path = result.metadata.get("search_path", "")
        
        # Add summary information
        if file_count == 0:
            result.content = f"No files found matching pattern '{pattern}' in '{search_path}'"
        elif file_count == 1:
            result.content = f"Found 1 file matching pattern '{pattern}':\n\n{result.content}"
        else:
            # For multiple files, add count and limit display if too many
            if file_count > 50:
                # Limit display to first 50 files for readability
                files = result.metadata["files"][:50]
                content = "\n".join(files)
                content += f"\n\n... and {file_count - 50} more files"
                result.content = f"Found {file_count} files matching pattern '{pattern}' (showing first 50):\n\n{content}"
                result.metadata["display_truncated"] = True
                result.metadata["displayed_count"] = 50
            else:
                result.content = f"Found {file_count} files matching pattern '{pattern}':\n\n{result.content}"
        
        return result