"""
GrepTool implementation for searching patterns in file contents.
"""

import os
import re
import glob
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from .base_tool import Tool, ToolExecutionResult


class GrepTool(Tool):
    """Tool for searching patterns in file contents using regex."""
    
    @classmethod
    def get_name(cls) -> str:
        return "grep"
    
    @classmethod
    def get_description(cls) -> str:
        return "Search for patterns in file contents using regular expressions"
    
    @classmethod
    def get_instructions(cls) -> str:
        return ("Use this tool to search for regex patterns within file contents. "
                "Returns list of files containing matches, sorted by modification time. "
                "Use 'include' parameter to filter which files to search (e.g., '*.py' for Python files). "
                "Patterns are case-sensitive regular expressions.")
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regular expression pattern to search for in file contents"
                },
                "path": {
                    "type": "string", 
                    "description": "Directory to search in (defaults to current working directory)",
                    "default": "."
                },
                "include": {
                    "type": "string",
                    "description": "Glob pattern to filter which files are searched (e.g., '*.py', '**/*.js')",
                    "default": None
                }
            },
            "required": ["pattern"]
        }
    
    def execute(self, tool_context=None, **kwargs) -> ToolExecutionResult:
        """
        Execute the grep search operation.
        
        Args:
            tool_context: ToolContext (not used but kept for compatibility)
            pattern: Regular expression pattern to search for
            path: Directory to search in (optional, defaults to cwd)
            include: Glob pattern for files to include (optional)
            
        Returns:
            ToolExecutionResult with list of files containing matches and metadata
        """
        pattern = kwargs.get("pattern")
        search_path = kwargs.get("path", ".")
        include_pattern = kwargs.get("include")
        
        if not pattern or not pattern.strip():
            return ToolExecutionResult(
                content="",
                success=False,
                error="Search pattern cannot be empty"
            )
        
        try:
            # Compile regex pattern
            try:
                compiled_pattern = re.compile(pattern, re.MULTILINE)
            except re.error as e:
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error=f"Invalid regular expression: {str(e)}"
                )
            
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
            
            # Find files to search
            files_to_search = self._get_files_to_search(base_path, include_pattern)
            
            # Search for pattern in files
            matching_files = self._search_files(compiled_pattern, files_to_search)
            
            # Sort by modification time (newest first)
            sorted_matches = self._sort_by_modification_time(matching_files)
            
            # Format output
            content = self._format_results(sorted_matches, pattern)
            
            # Extract just the file paths for metadata
            file_paths = [match["file_path"] for match in sorted_matches]
            
            # Prepare metadata
            metadata = {
                "pattern": pattern,
                "search_path": str(base_path),
                "include_pattern": include_pattern,
                "total_files_searched": len(files_to_search),
                "files_with_matches": len(sorted_matches),
                "matching_files": file_paths,
                "matches": sorted_matches
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
                error=f"Error during grep search: {str(e)}"
            )
    
    def _get_files_to_search(self, base_path: Path, include_pattern: Optional[str]) -> List[str]:
        """
        Get list of files to search based on include pattern.
        
        Args:
            base_path: Base directory to search in
            include_pattern: Glob pattern for files to include
            
        Returns:
            List of file paths to search
        """
        files_to_search = []
        
        if include_pattern:
            # Use glob pattern to filter files
            original_cwd = os.getcwd()
            try:
                os.chdir(base_path)
                
                if "**" in include_pattern:
                    matches = glob.glob(include_pattern, recursive=True)
                else:
                    matches = glob.glob(include_pattern)
                
                for match in matches:
                    match_path = Path(base_path) / match
                    if match_path.is_file() and self._is_text_file(match_path):
                        files_to_search.append(str(match_path))
                        
            finally:
                os.chdir(original_cwd)
        else:
            # Search all text files recursively
            for root, dirs, files in os.walk(base_path):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
                
                for file in files:
                    if not file.startswith('.'):  # Skip hidden files
                        file_path = Path(root) / file
                        if self._is_text_file(file_path):
                            files_to_search.append(str(file_path))
        
        return files_to_search
    
    def _is_text_file(self, file_path: Path) -> bool:
        """
        Check if a file is likely a text file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is likely text, False otherwise
        """
        # Skip files that are too large (>50MB)
        try:
            if file_path.stat().st_size > 50 * 1024 * 1024:
                return False
        except (OSError, IOError):
            return False
        
        # Check file extension for known text types
        text_extensions = {
            '.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json', '.xml',
            '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.log', '.sql',
            '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.dockerfile',
            '.go', '.rs', '.cpp', '.c', '.h', '.hpp', '.java', '.kt', '.scala',
            '.rb', '.php', '.pl', '.r', '.swift', '.dart', '.elm', '.clj', '.hs',
            '.ml', '.fs', '.vb', '.cs', '.m', '.mm', '.asm', '.s', '.makefile'
        }
        
        # Check extension
        if file_path.suffix.lower() in text_extensions:
            return True
        
        # Check for files without extension that might be text
        if not file_path.suffix:
            name = file_path.name.lower()
            if name in ['readme', 'license', 'changelog', 'makefile', 'dockerfile', 'jenkinsfile']:
                return True
        
        # For unknown extensions, try to read a small sample
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(1024)
                # If sample contains null bytes, it's likely binary
                if b'\x00' in sample:
                    return False
                # Try to decode as text
                try:
                    sample.decode('utf-8')
                    return True
                except UnicodeDecodeError:
                    try:
                        sample.decode('latin-1')
                        return True
                    except UnicodeDecodeError:
                        return False
        except (OSError, IOError):
            return False
    
    def _search_files(self, pattern: re.Pattern, files: List[str]) -> List[Dict[str, Any]]:
        """
        Search for pattern in the given files.
        
        Args:
            pattern: Compiled regex pattern
            files: List of file paths to search
            
        Returns:
            List of dictionaries containing match information
        """
        matching_files = []
        
        for file_path in files:
            try:
                matches = self._search_file(pattern, file_path)
                if matches:
                    matching_files.append({
                        "file_path": file_path,
                        "match_count": len(matches),
                        "matches": matches[:5],  # Limit to first 5 matches for display
                        "total_matches": len(matches)
                    })
            except Exception as e:
                # Skip files that can't be read
                continue
        
        return matching_files
    
    def _search_file(self, pattern: re.Pattern, file_path: str) -> List[Dict[str, Any]]:
        """
        Search for pattern in a single file.
        
        Args:
            pattern: Compiled regex pattern
            file_path: Path to the file to search
            
        Returns:
            List of match information dictionaries
        """
        matches = []
        
        try:
            # Try to read with UTF-8 first, then fall back to latin-1
            encodings = ['utf-8', 'latin-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                return []
            
            # Find all matches
            for match in pattern.finditer(content):
                line_start = content.rfind('\n', 0, match.start()) + 1
                line_end = content.find('\n', match.end())
                if line_end == -1:
                    line_end = len(content)
                
                line_content = content[line_start:line_end]
                line_number = content[:match.start()].count('\n') + 1
                
                matches.append({
                    "line_number": line_number,
                    "line_content": line_content.strip(),
                    "match_text": match.group(),
                    "match_start": match.start() - line_start,
                    "match_end": match.end() - line_start
                })
        
        except (OSError, IOError, MemoryError):
            # Skip files that can't be read or are too large
            pass
        
        return matches
    
    def _sort_by_modification_time(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort match results by file modification time (newest first).
        
        Args:
            matches: List of match dictionaries
            
        Returns:
            Sorted list of match dictionaries
        """
        def get_modification_time(match_dict: Dict[str, Any]) -> float:
            try:
                return os.path.getmtime(match_dict["file_path"])
            except (OSError, IOError):
                return 0.0
        
        return sorted(matches, key=get_modification_time, reverse=True)
    
    def _format_results(self, matches: List[Dict[str, Any]], pattern: str) -> str:
        """
        Format the search results for display.
        
        Args:
            matches: List of match dictionaries
            pattern: Original search pattern
            
        Returns:
            Formatted results string
        """
        if not matches:
            return f"No files found containing pattern '{pattern}'"
        
        # Create output showing files with matches
        lines = []
        lines.append(f"Found {len(matches)} file(s) containing pattern '{pattern}':")
        lines.append("")
        
        for i, match_info in enumerate(matches[:20]):  # Limit to first 20 files
            file_path = match_info["file_path"]
            match_count = match_info["match_count"]
            total_matches = match_info["total_matches"]
            
            # Convert to relative path if possible for cleaner display
            try:
                rel_path = os.path.relpath(file_path)
                if len(rel_path) < len(file_path):
                    display_path = rel_path
                else:
                    display_path = file_path
            except ValueError:
                display_path = file_path
            
            lines.append(f"{i+1}. {display_path}")
            
            if total_matches == 1:
                lines.append(f"   └─ 1 match")
            elif total_matches <= 5:
                lines.append(f"   └─ {total_matches} matches")
            else:
                lines.append(f"   └─ {total_matches} matches (showing first 5)")
            
            # Show first few matches with context
            for match in match_info["matches"]:
                line_num = match["line_number"]
                line_content = match["line_content"]
                
                # Truncate very long lines
                if len(line_content) > 100:
                    line_content = line_content[:100] + "..."
                
                lines.append(f"      Line {line_num}: {line_content}")
            
            lines.append("")
        
        if len(matches) > 20:
            lines.append(f"... and {len(matches) - 20} more files")
        
        return "\n".join(lines)
    
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
            return abs_path.startswith(cwd)
            
        except Exception:
            return False
    
    def post_process(self, result: ToolExecutionResult) -> ToolExecutionResult:
        """
        Post-process the grep search result.
        
        Args:
            result: Raw execution result
            
        Returns:
            Processed result with additional summary information
        """
        if not result.success or not result.metadata:
            return result
        
        # Add execution summary to content
        files_searched = result.metadata.get("total_files_searched", 0)
        files_with_matches = result.metadata.get("files_with_matches", 0)
        pattern = result.metadata.get("pattern", "")
        
        if files_with_matches == 0:
            summary = f"Searched {files_searched} files, no matches found for pattern '{pattern}'"
        else:
            summary = f"Searched {files_searched} files, found matches in {files_with_matches} file(s)"
        
        # Prepend summary to content
        result.content = f"{summary}\n\n{result.content}"
        
        return result