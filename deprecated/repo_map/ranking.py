"""
Simple File Ranking Algorithm
==============================

Simplified version of Aider's PageRank-based ranking system.
Ranks files by relevance using reference counting, mentions, and file importance.
"""

from collections import defaultdict, Counter
from typing import List, Dict, Set, Tuple
from pathlib import Path

try:
    from .repo_map import Tag
except ImportError:
    from repo_map import Tag


class SimpleRanker:
    """
    Simple file ranking algorithm based on references and importance.
    
    Simplified alternative to Aider's PageRank approach, focusing on
    practical relevance scoring without graph algorithms.
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def rank_files(
        self,
        tags_by_file: Dict[str, List[Tag]],
        chat_files: List[str],
        mentioned_files: Set[str],
        mentioned_idents: Set[str]
    ) -> List[Tuple[str, float]]:
        """
        Rank files by relevance score.
        
        Args:
            tags_by_file: Tags extracted for each file
            chat_files: Files currently in chat
            mentioned_files: Files mentioned in conversation  
            mentioned_idents: Identifiers mentioned in conversation
            
        Returns:
            List of (filename, score) tuples sorted by relevance
        """
        if self.verbose:
            print(f"Ranking {len(tags_by_file)} files")
        
        # Build reference graph
        definitions = defaultdict(set)  # ident -> set of files defining it
        references = defaultdict(list)  # ident -> list of files referencing it
        
        for filepath, tags in tags_by_file.items():
            for tag in tags:
                if tag.kind == 'def':
                    definitions[tag.name].add(filepath)
                elif tag.kind == 'ref':
                    references[tag.name].append(filepath)
        
        # Calculate file scores
        file_scores = {}
        chat_files_set = set(Path(f).name for f in chat_files)
        
        for filepath in tags_by_file.keys():
            score = self._calculate_file_score(
                filepath,
                tags_by_file[filepath],
                definitions,
                references,
                chat_files_set,
                mentioned_files,
                mentioned_idents
            )
            file_scores[filepath] = score
        
        # Sort by score (descending)
        ranked_files = sorted(
            file_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        if self.verbose:
            print(f"Top 5 ranked files:")
            for filepath, score in ranked_files[:5]:
                print(f"  {score:.3f}: {filepath}")
        
        return ranked_files
    
    def _calculate_file_score(
        self,
        filepath: str,
        tags: List[Tag],
        definitions: Dict[str, Set[str]],
        references: Dict[str, List[str]],
        chat_files: Set[str],
        mentioned_files: Set[str],
        mentioned_idents: Set[str]
    ) -> float:
        """Calculate relevance score for a single file."""
        score = 0.0
        
        # Base score for having content
        if tags:
            score += 1.0
        
        # Boost for important file types
        score += self._get_importance_boost(filepath)
        
        # Boost for mentioned files
        filename = Path(filepath).name
        if filepath in mentioned_files or filename in mentioned_files:
            score += 10.0
        
        # Boost for files in chat
        if filename in chat_files:
            score += 5.0
        
        # Score based on definitions and references
        defs_in_file = set()
        refs_from_file = []
        
        for tag in tags:
            if tag.kind == 'def':
                defs_in_file.add(tag.name)
            elif tag.kind == 'ref':
                refs_from_file.append(tag.name)
        
        # Boost for defining mentioned identifiers
        mentioned_defs = defs_in_file.intersection(mentioned_idents)
        score += len(mentioned_defs) * 5.0
        
        # Score based on reference patterns
        score += self._calculate_reference_score(
            filepath, defs_in_file, refs_from_file, definitions, references
        )
        
        # Score based on identifier naming patterns
        score += self._calculate_naming_score(defs_in_file, mentioned_idents)
        
        return score
    
    def _get_importance_boost(self, filepath: str) -> float:
        """Get importance boost based on file type and location."""
        path = Path(filepath)
        filename = path.name
        
        # Boost for important files
        important_files = {
            'readme.md', 'readme.txt', 'readme.rst', 'readme',
            'contributing.md', 'license', 'changelog.md',
            'requirements.txt', 'package.json', 'cargo.toml', 'pyproject.toml',
            'setup.py', 'makefile', '__init__.py', 'main.py', 'index.js'
        }
        
        if filename.lower() in important_files:
            return 5.0
        
        # Boost for files in root directory
        if len(path.parts) == 1:
            return 2.0
        
        # Boost for main/core files
        stem = path.stem.lower()
        if stem in {'main', 'app', 'core', 'index', 'server', 'client'}:
            return 3.0
        
        # Boost for test files (but not as much as main files)
        if 'test' in stem or stem.startswith('test_'):
            return 1.0
        
        return 0.0
    
    def _calculate_reference_score(
        self,
        filepath: str,
        defs_in_file: Set[str],
        refs_from_file: List[str],
        definitions: Dict[str, Set[str]],
        references: Dict[str, List[str]]
    ) -> float:
        """Calculate score based on reference patterns."""
        score = 0.0
        
        # Score for being referenced by other files
        incoming_refs = 0
        for ident in defs_in_file:
            if ident in references:
                # Count how many other files reference this definition
                other_files_refs = [f for f in references[ident] if f != filepath]
                incoming_refs += len(other_files_refs)
        
        # Logarithmic scaling to avoid over-weighting heavily referenced files
        if incoming_refs > 0:
            score += min(5.0, 1.0 + 2.0 * (incoming_refs ** 0.5))
        
        # Score for referencing external definitions
        external_refs = 0
        for ident in refs_from_file:
            if ident in definitions:
                # Check if this identifier is defined elsewhere
                defining_files = definitions[ident]
                if defining_files and filepath not in defining_files:
                    external_refs += 1
        
        if external_refs > 0:
            score += min(3.0, 0.5 + 1.0 * (external_refs ** 0.5))
        
        return score
    
    def _calculate_naming_score(
        self, 
        defs_in_file: Set[str], 
        mentioned_idents: Set[str]
    ) -> float:
        """Calculate score based on identifier naming patterns."""
        score = 0.0
        
        for ident in defs_in_file:
            # Boost for well-structured identifiers
            if self._is_well_named(ident):
                score += 0.5
            
            # Boost for matching mentioned identifier patterns
            if mentioned_idents:
                for mentioned in mentioned_idents:
                    if self._names_related(ident, mentioned):
                        score += 2.0
                        break
        
        return score
    
    def _is_well_named(self, ident: str) -> bool:
        """Check if identifier follows good naming conventions."""
        if len(ident) < 3:
            return False
        
        # Check for common patterns
        has_underscore = '_' in ident
        has_camelcase = any(c.isupper() for c in ident[1:]) and any(c.islower() for c in ident)
        is_descriptive = len(ident) >= 5
        
        return (has_underscore or has_camelcase) and is_descriptive
    
    def _names_related(self, name1: str, name2: str) -> bool:
        """Check if two names are related (simple heuristic)."""
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        # Direct substring match
        if name1_lower in name2_lower or name2_lower in name1_lower:
            return True
        
        # Check for common word parts (split on underscore/camelcase)
        parts1 = self._split_identifier(name1_lower)
        parts2 = self._split_identifier(name2_lower)
        
        # If they share any significant word parts
        common_parts = set(parts1) & set(parts2)
        significant_parts = {p for p in common_parts if len(p) >= 3}
        
        return len(significant_parts) > 0
    
    def _split_identifier(self, ident: str) -> List[str]:
        """Split identifier into word parts."""
        import re
        
        # Split on underscores
        parts = ident.split('_')
        
        # Further split camelCase
        result = []
        for part in parts:
            # Split camelCase using regex
            subparts = re.findall(r'[a-z]+|[A-Z][a-z]*', part)
            result.extend([p.lower() for p in subparts if p])
        
        return [p for p in result if len(p) >= 2]