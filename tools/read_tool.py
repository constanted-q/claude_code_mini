"""
ReadTool implementation for reading text files with encoding detection.
"""

import os
import chardet
from pathlib import Path
from typing import Dict, Any
from .base_tool import Tool, ToolExecutionResult


class ReadTool(Tool):
    """Tool for reading text files with automatic encoding detection."""
    
    @classmethod
    def get_name(cls) -> str:
        return "read_file"
    
    @classmethod
    def get_description(cls) -> str:
        return "Read the contents of a text file with automatic encoding detection"
    
    @classmethod
    def get_instructions(cls) -> str:
        return ("Use this tool to read the contents of text files. Provide the file path as a parameter. "
                "The tool will automatically detect the file encoding and return the content along with "
                "metadata about the file (size, encoding, modification time).")
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the text file to read (absolute or relative path)"
                },
                "offset": {
                    "type": "integer",
                    "description": "Starting line number (1-based, optional)",
                    "default": 1,
                    "minimum": 1
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum lines to read (default: 2000)",
                    "default": 2000,
                    "minimum": 1,
                    "maximum": 10000
                },
                "max_size_mb": {
                    "type": "integer", 
                    "description": "Maximum file size to read in MB (default: 10)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100
                }
            },
            "required": ["file_path"]
        }
    
    def execute(self, **kwargs) -> ToolExecutionResult:
        """
        Execute the file reading operation.
        
        Args:
            file_path: Path to the file to read
            offset: Starting line number (1-based, default: 1)
            limit: Maximum lines to read (default: 2000)
            max_size_mb: Maximum file size in MB (default: 10)
            
        Returns:
            ToolExecutionResult with file contents and metadata
        """
        file_path = kwargs.get("file_path")
        offset = kwargs.get("offset", 1)
        limit = kwargs.get("limit", 2000)
        max_size_mb = kwargs.get("max_size_mb", 10)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        try:
            # Resolve and validate path
            path = Path(file_path).resolve()
            
            # Security check: prevent path traversal attacks
            if not self._is_safe_path(str(path)):
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error="Access denied: path traversal not allowed"
                )
            
            # Check if file exists
            if not path.exists():
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error=f"File not found: {file_path}"
                )
            
            # Check if it's a file (not directory)
            if not path.is_file():
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error=f"Path is not a file: {file_path}"
                )
            
            # Get file stats
            file_stats = path.stat()
            file_size = file_stats.st_size
            
            # Check file size
            if file_size > max_size_bytes:
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error=f"File too large: {file_size} bytes (max: {max_size_bytes} bytes)"
                )
            
            # Detect encoding
            encoding = self._detect_encoding(path)
            
            # Read file content with line-based processing
            try:
                content_lines = []
                line_count = 0
                lines_read = 0
                truncated = False
                
                with open(path, 'r', encoding=encoding) as f:
                    for line in f:
                        line_count += 1
                        
                        # Skip lines before offset
                        if line_count < offset:
                            continue
                        
                        # Stop if we've read enough lines
                        if lines_read >= limit:
                            truncated = True
                            break
                        
                        # Remove trailing newline for consistent formatting
                        line_content = line.rstrip('\n\r')
                        
                        # Truncate very long lines
                        if len(line_content) > 2000:
                            line_content = line_content[:2000] + "... (line truncated)"
                        
                        # Format with line numbers (cat -n style)
                        formatted_line = f"{line_count}\t{line_content}"
                        content_lines.append(formatted_line)
                        lines_read += 1
                
                # Join all formatted lines
                content = '\n'.join(content_lines)
                
                # Add truncation notice if needed
                if truncated:
                    content += f"\n\n... (truncated after {lines_read} lines, starting from line {offset})"
                    
            except UnicodeDecodeError:
                # Fallback to binary read if encoding detection fails
                encoding = "binary"
                with open(path, 'rb') as f:
                    raw_content = f.read()
                content = f"<Binary file content - {len(raw_content)} bytes>"
                line_count = 0
                lines_read = 0
                truncated = False
            
            # Prepare metadata
            metadata = {
                "file_path": str(path),
                "file_size": file_size,
                "encoding": encoding,
                "modification_time": file_stats.st_mtime,
                "total_lines": line_count if encoding != "binary" else None,
                "lines_read": lines_read if encoding != "binary" else None,
                "offset": offset,
                "limit": limit,
                "truncated": truncated
            }
            
            return ToolExecutionResult(
                content=content,
                success=True,
                metadata=metadata
            )
            
        except PermissionError:
            return ToolExecutionResult(
                content="",
                success=False,
                error=f"Permission denied: cannot read {file_path}"
            )
        except OSError as e:
            return ToolExecutionResult(
                content="",
                success=False,
                error=f"OS error reading file: {str(e)}"
            )
        except Exception as e:
            return ToolExecutionResult(
                content="",
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    def _detect_encoding(self, path: Path) -> str:
        """
        Detect file encoding using multiple strategies.
        
        Args:
            path: Path to the file
            
        Returns:
            Detected encoding string
        """
        # Read a sample of the file for detection
        sample_size = min(8192, path.stat().st_size)
        
        try:
            with open(path, 'rb') as f:
                raw_data = f.read(sample_size)
            
            # Use chardet for detection
            detected = chardet.detect(raw_data)
            confidence = detected.get('confidence', 0)
            encoding = detected.get('encoding', 'utf-8')
            
            # If confidence is high, use detected encoding
            if confidence > 0.7 and encoding:
                return encoding
            
            # Fallback strategy: try common encodings
            encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'ascii']
            
            for enc in encodings_to_try:
                try:
                    raw_data.decode(enc)
                    return enc
                except UnicodeDecodeError:
                    continue
            
            # If all fail, default to utf-8 with error handling
            return 'utf-8'
            
        except Exception:
            return 'utf-8'
    
    def _is_safe_path(self, path: str) -> bool:
        """
        Check if the path is safe (no path traversal).
        
        Args:
            path: File path to check
            
        Returns:
            True if path is safe, False otherwise
        """
        try:
            # Get absolute path
            abs_path = os.path.abspath(path)
            
            # Get current working directory
            cwd = os.getcwd()
            
            # Check if the file is within allowed directories
            # Allow current directory and subdirectories
            return abs_path.startswith(cwd)
            
        except Exception:
            return False
    
    def post_process(self, result: ToolExecutionResult) -> ToolExecutionResult:
        """
        Post-process the file reading result.
        
        Args:
            result: Raw execution result
            
        Returns:
            Processed result with formatted content
        """
        if not result.success:
            return result
        
        # Add content preview for very long files
        content = result.content
        if len(content) > 10000:  # If content is longer than 10k characters
            preview_size = 5000
            result.metadata["content_truncated"] = True
            result.metadata["original_length"] = len(content)
            result.content = (
                content[:preview_size] + 
                f"\n\n[... Content truncated. Original length: {len(content)} characters, "
                f"showing first {preview_size} characters ...]"
            )
        
        # Add file type hint based on extension
        if "file_path" in result.metadata:
            file_path = result.metadata["file_path"]
            extension = Path(file_path).suffix.lower()
            if extension:
                result.metadata["file_type"] = extension[1:]  # Remove the dot
        
        return result