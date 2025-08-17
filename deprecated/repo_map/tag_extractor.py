"""
Tag Extraction Component
========================

Simplified code analysis for extracting definitions and references.
Uses Python AST for Python files and regex patterns for other languages.
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Set, Dict, Optional

try:
    from .repo_map import Tag
except ImportError:
    from repo_map import Tag


class TagExtractor:
    """
    Extracts definitions and references from source code files.
    
    Simplified approach compared to Aider's tree-sitter implementation,
    but captures the essential functionality for creating repository maps.
    """
    
    def __init__(self, root_dir: str, verbose: bool = False):
        self.root = Path(root_dir)
        self.verbose = verbose
        
        # Language-specific patterns for definitions and references
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize regex patterns for different languages."""
        
        # JavaScript/TypeScript patterns
        self.js_patterns = {
            'def': [
                r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)',  # function declarations
                r'^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\()',  # function expressions
                r'^\s*(?:export\s+)?class\s+(\w+)',  # class declarations
                r'^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=',  # variable declarations
                r'^\s*(\w+)\s*:\s*(?:function|\()',  # object method definitions
            ],
            'ref': r'\b([a-zA-Z_]\w*)\b'  # identifier references
        }
        
        # Go patterns
        self.go_patterns = {
            'def': [
                r'^\s*func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)',  # function declarations
                r'^\s*type\s+(\w+)\s+(?:struct|interface)',  # type declarations
                r'^\s*var\s+(\w+)',  # variable declarations
                r'^\s*const\s+(\w+)',  # constant declarations
            ],
            'ref': r'\b([A-Za-z_]\w*)\b'
        }
        
        # Rust patterns
        self.rust_patterns = {
            'def': [
                r'^\s*(?:pub\s+)?fn\s+(\w+)',  # function definitions
                r'^\s*(?:pub\s+)?struct\s+(\w+)',  # struct definitions
                r'^\s*(?:pub\s+)?enum\s+(\w+)',  # enum definitions
                r'^\s*(?:pub\s+)?trait\s+(\w+)',  # trait definitions
                r'^\s*(?:pub\s+)?mod\s+(\w+)',  # module definitions
                r'^\s*(?:pub\s+)?type\s+(\w+)',  # type aliases
            ],
            'ref': r'\b([a-zA-Z_]\w*)\b'
        }
        
        # Java patterns
        self.java_patterns = {
            'def': [
                r'^\s*(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*(?:class|interface)\s+(\w+)',
                r'^\s*(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*\w+\s+(\w+)\s*\(',  # methods
                r'^\s*(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*\w+\s+(\w+)\s*[;=]',  # fields
            ],
            'ref': r'\b([A-Za-z_]\w*)\b'
        }
        
        # Generic C-style patterns (C, C++, C#)
        self.c_style_patterns = {
            'def': [
                r'^\s*(?:static\s+)?(?:inline\s+)?(?:extern\s+)?\w+\s+(\w+)\s*\(',  # function definitions
                r'^\s*(?:typedef\s+)?(?:struct|class|union|enum)\s+(\w+)',  # type definitions
                r'^\s*#define\s+(\w+)',  # macro definitions
            ],
            'ref': r'\b([a-zA-Z_]\w*)\b'
        }
    
    def extract_tags(self, filepath: str, rel_filepath: str) -> List[Tag]:
        """
        Extract tags (definitions and references) from a source file.
        
        Args:
            filepath: Absolute path to the file
            rel_filepath: Relative path from repository root
            
        Returns:
            List of Tag objects
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except (IOError, OSError) as e:
            if self.verbose:
                print(f"Error reading {filepath}: {e}")
            return []
        
        if not content.strip():
            return []
        
        file_ext = Path(filepath).suffix.lower()
        
        # Use Python AST for Python files
        if file_ext == '.py':
            return self._extract_python_tags(filepath, rel_filepath, content)
        
        # Use regex patterns for other languages
        return self._extract_generic_tags(filepath, rel_filepath, content, file_ext)
    
    def _extract_python_tags(self, filepath: str, rel_filepath: str, content: str) -> List[Tag]:
        """Extract tags from Python files using AST."""
        tags = []
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            if self.verbose:
                print(f"Syntax error in {filepath}, falling back to regex")
            return self._extract_generic_tags(filepath, rel_filepath, content, '.py')
        
        # Extract definitions using AST visitor
        visitor = PythonTagVisitor(filepath, rel_filepath)
        visitor.visit(tree)
        tags.extend(visitor.tags)
        
        # Extract references using simple regex
        ref_pattern = r'\b([a-zA-Z_]\w*)\b'
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines, 1):
            for match in re.finditer(ref_pattern, line):
                name = match.group(1)
                # Filter out keywords and common built-ins
                if not self._is_python_keyword(name):
                    tags.append(Tag(
                        rel_fname=rel_filepath,
                        fname=filepath,
                        line=line_num,
                        name=name,
                        kind='ref'
                    ))
        
        return tags
    
    def _extract_generic_tags(self, filepath: str, rel_filepath: str, content: str, file_ext: str) -> List[Tag]:
        """Extract tags using regex patterns for non-Python files."""
        tags = []
        
        # Select appropriate patterns based on file extension
        patterns = self._get_patterns_for_extension(file_ext)
        if not patterns:
            return tags
        
        lines = content.splitlines()
        
        # Extract definitions
        for line_num, line in enumerate(lines, 1):
            for def_pattern in patterns['def']:
                for match in re.finditer(def_pattern, line):
                    name = match.group(1)
                    if name and name.isalpha():  # Basic filtering
                        tags.append(Tag(
                            rel_fname=rel_filepath,
                            fname=filepath,
                            line=line_num,
                            name=name,
                            kind='def'
                        ))
        
        # Extract references (simplified - just find identifiers)
        ref_pattern = patterns['ref']
        for line_num, line in enumerate(lines, 1):
            # Skip comments and strings (very basic)
            if '//' in line:
                line = line[:line.index('//')]
            if '/*' in line:
                continue  # Skip multi-line comments (simplified)
            
            for match in re.finditer(ref_pattern, line):
                name = match.group(1)
                if (name and name.isalpha() and 
                    not self._is_common_keyword(name, file_ext)):
                    tags.append(Tag(
                        rel_fname=rel_filepath,
                        fname=filepath,
                        line=line_num,
                        name=name,
                        kind='ref'
                    ))
        
        return tags
    
    def _get_patterns_for_extension(self, ext: str) -> Optional[Dict]:
        """Get regex patterns for a file extension."""
        pattern_map = {
            '.js': self.js_patterns,
            '.jsx': self.js_patterns,
            '.ts': self.js_patterns,
            '.tsx': self.js_patterns,
            '.go': self.go_patterns,
            '.rs': self.rust_patterns,
            '.java': self.java_patterns,
            '.c': self.c_style_patterns,
            '.cpp': self.c_style_patterns,
            '.cxx': self.c_style_patterns,
            '.cc': self.c_style_patterns,
            '.h': self.c_style_patterns,
            '.hpp': self.c_style_patterns,
            '.cs': self.c_style_patterns,
        }
        return pattern_map.get(ext)
    
    def _is_python_keyword(self, name: str) -> bool:
        """Check if name is a Python keyword or common built-in."""
        keywords = {
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 
            'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 
            'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 
            'try', 'while', 'with', 'yield',
            # Common built-ins
            'int', 'str', 'list', 'dict', 'set', 'tuple', 'bool', 'float',
            'len', 'range', 'print', 'open', 'type', 'isinstance'
        }
        return name in keywords
    
    def _is_common_keyword(self, name: str, ext: str) -> bool:
        """Check if name is a common keyword for the given language."""
        # Very basic keyword filtering
        common_keywords = {
            'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
            'break', 'continue', 'return', 'function', 'var', 'let', 'const',
            'class', 'struct', 'enum', 'interface', 'public', 'private',
            'static', 'void', 'int', 'string', 'bool', 'true', 'false',
            'null', 'undefined', 'this', 'super', 'new', 'delete'
        }
        return name.lower() in common_keywords


class PythonTagVisitor(ast.NodeVisitor):
    """AST visitor for extracting Python definitions."""
    
    def __init__(self, filepath: str, rel_filepath: str):
        self.filepath = filepath
        self.rel_filepath = rel_filepath
        self.tags = []
    
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        self.tags.append(Tag(
            rel_fname=self.rel_filepath,
            fname=self.filepath,
            line=node.lineno,
            name=node.name,
            kind='def'
        ))
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Visit async function definitions."""
        self.tags.append(Tag(
            rel_fname=self.rel_filepath,
            fname=self.filepath,
            line=node.lineno,
            name=node.name,
            kind='def'
        ))
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        self.tags.append(Tag(
            rel_fname=self.rel_filepath,
            fname=self.filepath,
            line=node.lineno,
            name=node.name,
            kind='def'
        ))
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        """Visit variable assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.tags.append(Tag(
                    rel_fname=self.rel_filepath,
                    fname=self.filepath,
                    line=node.lineno,
                    name=target.id,
                    kind='def'
                ))
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Visit import statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.tags.append(Tag(
                rel_fname=self.rel_filepath,
                fname=self.filepath,
                line=node.lineno,
                name=name,
                kind='def'
            ))
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Visit from...import statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            if name != '*':  # Skip wildcard imports
                self.tags.append(Tag(
                    rel_fname=self.rel_filepath,
                    fname=self.filepath,
                    line=node.lineno,
                    name=name,
                    kind='def'
                ))
        self.generic_visit(node)