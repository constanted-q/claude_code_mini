"""
EditTool implementation for precise file editing with validation and diff generation.
"""

import os
import re
import difflib
from pathlib import Path
from typing import Dict, Any
from .base_tool import Tool, ToolExecutionResult


class EditTool(Tool):
    """Tool for making precise edits to text files with validation."""
    
    @classmethod
    def get_name(cls) -> str:
        return "edit_file"
    
    @classmethod
    def get_description(cls) -> str:
        return "Edit a text file by replacing exact string matches with new content"
    
    @classmethod
    def get_instructions(cls) -> str:
        return (
            "Use this tool to make precise edits to files. The file must be read with read_file first. "
            "Provide the exact string to replace (old_string) and the replacement text (new_string). "
            "If the file content shown includes line numbers (e.g., '123\tcode'), do NOT include the line "
            "numbers in old_string - only include the actual file content. "
            "Set expected_replacements to control how many occurrences should be replaced (default: 1)."
        )
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit (must have been read first)"
                },
                "old_string": {
                    "type": "string",
                    "description": "Exact string to replace (without line numbers if shown in read output)"
                },
                "new_string": {
                    "type": "string",
                    "description": "String to replace old_string with"
                },
                "expected_replacements": {
                    "type": "integer",
                    "description": "Expected number of replacements (default: 1)",
                    "default": 1,
                    "minimum": 1
                }
            },
            "required": ["file_path", "old_string", "new_string"]
        }
    
    def execute(self, tool_context=None, **kwargs) -> ToolExecutionResult:
        """
        Execute the file editing operation.
        
        Args:
            tool_context: ToolContext with cached file states
            file_path: Path to the file to edit
            old_string: String to replace
            new_string: Replacement string
            expected_replacements: Expected number of replacements
            
        Returns:
            ToolExecutionResult with diff and metadata
        """
        file_path = kwargs.get("file_path")
        old_string = kwargs.get("old_string")
        new_string = kwargs.get("new_string")
        expected_replacements = kwargs.get("expected_replacements", 1)
        
        try:
            # Validate tool context is provided
            if tool_context is None:
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error="EditTool requires ToolContext to track file states"
                )
            
            # Resolve path
            path = Path(file_path).resolve()
            path_str = str(path)
            
            # Validation 1: File must have been read first
            if not tool_context.is_file_cached(path_str):
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error=f"File must be read with read_file tool before editing: {file_path}"
                )
            
            # Get cached file info
            cached_file = tool_context.get_cached_file(path_str)
            cached_content = cached_file["content"]
            cached_timestamp = cached_file["timestamp"]
            cached_encoding = cached_file["encoding"]
            
            # Validation 2: Check if file has been modified externally
            if cached_timestamp is not None:
                try:
                    current_stats = path.stat()
                    if current_stats.st_mtime != cached_timestamp:
                        return ToolExecutionResult(
                            content="",
                            success=False,
                            error=f"File has been modified externally since last read. Please read the file again to see current content."
                        )
                except OSError:
                    return ToolExecutionResult(
                        content="",
                        success=False,
                        error=f"File no longer exists or is inaccessible: {file_path}"
                    )
            
            # Validation 3: Strip line numbers from old_string if present
            cleaned_old_string = self._strip_line_numbers(old_string)
            if cleaned_old_string != old_string:
                # Inform user about line number stripping
                validation_message = f"Detected and removed line number prefix from old_string"
                old_string = cleaned_old_string
            
            # Validation 4: No-op check
            if old_string == new_string:
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error="old_string and new_string are identical. No changes would be made."
                )
            
            # Validation 5: Empty old_string check
            if old_string == "":
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error="Empty old_string not allowed. Use write_file tool for new content."
                )
            
            # Validation 6: Check occurrence count
            occurrences = self._count_occurrences(cached_content, old_string)
            
            if occurrences == 0:
                # Try to provide helpful suggestions
                suggestion = self._find_similar_strings(cached_content, old_string)
                error_msg = f"old_string not found in file. Ensure exact match including whitespace."
                if suggestion:
                    error_msg += f"\n\nSimilar content found:\n{suggestion}"
                
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error=error_msg
                )
            
            if occurrences != expected_replacements:
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error=f"Expected {expected_replacements} replacement(s) but found {occurrences} occurrence(s). "
                           f"Set expected_replacements to {occurrences} or refine old_string to be more specific."
                )
            
            # Perform the replacement
            new_content = self._perform_replacement(cached_content, old_string, new_string, expected_replacements)
            
            # Generate diff
            diff = self._generate_diff(cached_content, new_content, path_str)
            
            # Ask user for permission before making changes
            if not self._ask_user_permission(path_str, old_string, new_string, expected_replacements, diff):
                return ToolExecutionResult(
                    content="Edit cancelled by user",
                    success=False,
                    error="User denied permission to edit the file"
                )
            
            # Write the file preserving encoding
            try:
                with open(path, 'w', encoding=cached_encoding) as f:
                    f.write(new_content)
            except Exception as e:
                return ToolExecutionResult(
                    content="",
                    success=False,
                    error=f"Failed to write file: {str(e)}"
                )
            
            # Update cached file state
            tool_context.cache_file_state(path_str, new_content, cached_encoding)
            
            # Generate context snippet around changes
            snippet = self._generate_context_snippet(new_content, new_string)
            
            # Prepare result content
            result_content = f"File edited successfully. {expected_replacements} replacement(s) made.\n\n"
            result_content += f"Diff:\n{diff}\n\n"
            result_content += f"Context around changes:\n{snippet}"
            print(f"###debug: {result_content}")
            
            metadata = {
                "file_path": path_str,
                "replacements_made": expected_replacements,
                "old_string_length": len(old_string),
                "new_string_length": len(new_string),
                "file_size_before": len(cached_content),
                "file_size_after": len(new_content)
            }
            
            return ToolExecutionResult(
                content=result_content,
                success=True,
                metadata=metadata
            )
            
        except Exception as e:
            return ToolExecutionResult(
                content="",
                success=False,
                error=f"Unexpected error during file edit: {str(e)}"
            )
    
    def _strip_line_numbers(self, text: str) -> str:
        """
        Strip line number prefixes from text if present.
        
        Args:
            text: Text that might contain line number prefixes
            
        Returns:
            Text with line numbers stripped
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Check for line number pattern at start: digits + tab
            match = re.match(r'^\d+\t(.*)$', line)
            if match:
                cleaned_lines.append(match.group(1))
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _count_occurrences(self, content: str, search_string: str) -> int:
        """Count exact occurrences of search_string in content."""
        return content.count(search_string)
    
    def _find_similar_strings(self, content: str, target: str, max_suggestions: int = 3) -> str:
        """
        Find similar strings in content to help with debugging.
        
        Args:
            content: File content to search
            target: Target string that wasn't found
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            Formatted string with suggestions
        """
        lines = content.split('\n')
        suggestions = []
        target_words = target.lower().split()
        
        if not target_words:
            return ""
        
        # Look for lines containing some of the target words
        for i, line in enumerate(lines):
            line_lower = line.lower()
            word_matches = sum(1 for word in target_words if word in line_lower)
            
            # If line contains at least half the words, consider it a suggestion
            if word_matches >= len(target_words) // 2:
                suggestions.append(f"Line {i+1}: {line.strip()}")
                
                if len(suggestions) >= max_suggestions:
                    break
        
        if suggestions:
            return '\n'.join(suggestions)
        else:
            return ""
    
    def _perform_replacement(self, content: str, old_string: str, new_string: str, limit: int) -> str:
        """
        Perform string replacement with occurrence limit.
        
        Args:
            content: Original content
            old_string: String to replace
            new_string: Replacement string
            limit: Maximum number of replacements
            
        Returns:
            Modified content
        """
        result = content
        count = 0
        
        # Replace occurrences one by one to respect limit
        while count < limit:
            index = result.find(old_string)
            if index == -1:
                break
            
            # Replace this occurrence
            result = result[:index] + new_string + result[index + len(old_string):]
            count += 1
            
            # Update search position to avoid replacing the new content
            # This is important for cases where new_string contains old_string
        
        return result
    
    def _generate_diff(self, old_content: str, new_content: str, filename: str) -> str:
        """
        Generate a unified diff between old and new content.
        
        Args:
            old_content: Original file content
            new_content: Modified file content
            filename: Name of the file for diff headers
            
        Returns:
            Unified diff string
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{filename} (before)",
            tofile=f"{filename} (after)",
            lineterm='',
            n=3  # 3 lines of context
        )
        
        return ''.join(diff)
    
    def _ask_user_permission(self, file_path: str, old_string: str, new_string: str, expected_replacements: int, diff: str) -> bool:
        """
        Ask user for permission to proceed with file edit.
        
        Args:
            file_path: Path to the file being edited
            old_string: String being replaced
            new_string: Replacement string
            expected_replacements: Number of replacements to be made
            diff: Generated diff showing changes
            
        Returns:
            True if user grants permission, False otherwise
        """
        print("\n" + "="*60)
        print("🚨 EDIT PERMISSION REQUIRED")
        print("="*60)
        print(f"File: {file_path}")
        print(f"Replacements: {expected_replacements}")
        print(f"Old text: {repr(old_string[:100])}{'...' if len(old_string) > 100 else ''}")
        print(f"New text: {repr(new_string[:100])}{'...' if len(new_string) > 100 else ''}")
        print("\nProposed changes:")
        print("-" * 60)
        print(diff if diff.strip() else "No diff available")
        print("-" * 60)
        
        while True:
            try:
                response = input("\n⚠️  Do you want to proceed with this edit? (y/n): ").strip().lower()
                if response in ['y', 'yes']:
                    print("✅ Edit approved by user")
                    return True
                elif response in ['n', 'no']:
                    print("❌ Edit denied by user")
                    return False
                else:
                    print("Please enter 'y' or 'n'")
            except (KeyboardInterrupt, EOFError):
                print("\n❌ Edit cancelled by user")
                return False
    
    def _generate_context_snippet(self, content: str, changed_text: str, context_lines: int = 5) -> str:
        """
        Generate a snippet showing context around the changed text.
        
        Args:
            content: Full file content after changes
            changed_text: The text that was inserted
            context_lines: Number of context lines to show
            
        Returns:
            Formatted snippet with line numbers
        """
        lines = content.split('\n')
        
        # Find lines containing the changed text
        changed_line_indices = []
        for i, line in enumerate(lines):
            if changed_text and changed_text in line:
                changed_line_indices.append(i)
        
        if not changed_line_indices:
            # If we can't find the changed text, show first few lines
            start = 0
            end = min(context_lines * 2, len(lines))
        else:
            # Show context around first occurrence
            first_change = changed_line_indices[0]
            start = max(0, first_change - context_lines)
            end = min(len(lines), first_change + context_lines + 1)
        
        snippet_lines = []
        for i in range(start, end):
            line_num = i + 1
            line_content = lines[i]
            
            # Mark changed lines
            if i in changed_line_indices:
                snippet_lines.append(f"→ {line_num:3d}: {line_content}")
            else:
                snippet_lines.append(f"  {line_num:3d}: {line_content}")
        
        return '\n'.join(snippet_lines)