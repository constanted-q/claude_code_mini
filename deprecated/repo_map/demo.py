"""
Repository Map Demo
===================

Demonstration of the minimalist repository map implementation.
Shows how to analyze a codebase and generate intelligent context maps.
"""

import sys
import argparse
from pathlib import Path

# Handle imports for both package and direct execution
try:
    from .repo_map import RepoMap
except ImportError:
    from repo_map import RepoMap


def main():
    parser = argparse.ArgumentParser(
        description="Generate repository map for code understanding"
    )
    parser.add_argument(
        "directory",
        nargs="?", 
        default=".",
        help="Directory to analyze (default: current directory)"
    )
    parser.add_argument(
        "--max-tokens", 
        type=int, 
        default=1024,
        help="Maximum tokens for output (default: 1024)"
    )
    parser.add_argument(
        "--chat-files", 
        nargs="*", 
        default=[],
        help="Files currently in chat context"
    )
    parser.add_argument(
        "--mentioned", 
        nargs="*", 
        default=[],
        help="Files or identifiers mentioned in conversation"
    )
    parser.add_argument(
        "--verbose", 
        "-v", 
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--refresh", 
        action="store_true",
        help="Force refresh, bypass cache"
    )
    parser.add_argument(
        "--stats", 
        action="store_true",
        help="Show statistics"
    )
    
    args = parser.parse_args()
    
    # Initialize repository map
    repo_map = RepoMap(
        root_dir=args.directory,
        max_tokens=args.max_tokens,
        verbose=args.verbose
    )
    
    print(f"Analyzing repository: {Path(args.directory).resolve()}")
    print(f"Token budget: {args.max_tokens}")
    
    if args.chat_files:
        print(f"Chat files: {args.chat_files}")
    
    if args.mentioned:
        print(f"Mentioned: {args.mentioned}")
    
    print("\n" + "="*60)
    
    # Split mentioned items into files and identifiers
    mentioned_files = set()
    mentioned_idents = set()
    
    for item in args.mentioned:
        if '.' in item or '/' in item:
            mentioned_files.add(item)
        else:
            mentioned_idents.add(item)
    
    # Generate repository map
    try:
        context = repo_map.generate_map(
            chat_files=args.chat_files,
            mentioned_files=mentioned_files,
            mentioned_idents=mentioned_idents,
            force_refresh=args.refresh
        )
        
        if context:
            print(context)
        else:
            print("No repository context generated (no relevant files found)")
        
        if args.stats:
            print("\n" + "="*60)
            print("Statistics:")
            stats = repo_map.get_stats()
            for key, value in stats.items():
                print(f"  {key}: {value}")
    
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error generating repository map: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def demo_scenarios():
    """Demonstrate different usage scenarios."""
    print("Repository Map Demo Scenarios")
    print("="*40)
    
    # Scenario 1: Basic analysis
    print("\n1. Basic Repository Analysis")
    print("-" * 30)
    repo_map = RepoMap(max_tokens=500, verbose=True)
    context = repo_map.generate_map()
    print("Generated context (truncated):")
    print(context[:300] + "..." if len(context) > 300 else context)
    
    # Scenario 2: With mentioned identifiers
    print("\n2. With Mentioned Identifiers")
    print("-" * 30)
    context = repo_map.generate_map(
        mentioned_idents={"RepoMap", "extract_tags", "generate_map"}
    )
    print("Generated context focusing on mentioned identifiers:")
    print(context[:300] + "..." if len(context) > 300 else context)
    
    # Scenario 3: Performance comparison
    print("\n3. Performance Statistics")
    print("-" * 30)
    stats = repo_map.get_stats()
    print("Repository analysis statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments - run demo scenarios
        demo_scenarios()
    else:
        # Run with command line arguments
        main()