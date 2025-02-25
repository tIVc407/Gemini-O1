#!/usr/bin/env python3
"""
Migration script to help transition from the old structure to the new one.

This script provides a simple way to:
1. Run the application with the new structure
2. Get help on how to use the new structure
"""

import os
import sys
import argparse

def print_migration_guide():
    """Print a guide for migrating to the new structure."""
    print("""
Gemini-O1 Migration Guide
=========================

The codebase has been refactored into a more modular structure to improve maintainability.

Key changes:
-----------
1. All code is now organized into the 'gemini_o1' package
2. Entry points have changed:
   - CLI: Use 'python main.py' instead of 'python beep.py'
   - Web: Use 'python -m gemini_o1.ui.web_interface' instead of 'python web_interface.py'

3. Import paths have changed:
   - Old: from beep import GeminiNetwork, GeminiInstance
   - New: from gemini_o1 import GeminiNetwork, GeminiInstance

File structure:
--------------
gemini_o1/
├── models/          - Core data models (Network and Instance)
├── commands/        - Command parsing and handling
├── communication/   - Response generation
├── ui/              - CLI and web interfaces
└── utils/           - Utilities (prompts, rate limiting, etc.)

To start using the new structure:
--------------------------------
- CLI interface: python main.py interactive
- Web interface: python -m gemini_o1.ui.web_interface
- Run tests: python -m pytest test_gemini_o1.py
""")

def run_cli():
    """Run the CLI application with the new structure."""
    try:
        from gemini_o1 import GeminiNetwork
        import asyncio
        from gemini_o1.ui.cli import cli_main
        
        async def main():
            async with GeminiNetwork() as network:
                await cli_main(network)
                
        asyncio.run(main())
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("Make sure the gemini_o1 package is in your Python path.")
        sys.exit(1)
    except Exception as e:
        print(f"Error running CLI: {e}")
        sys.exit(1)

def run_web():
    """Run the web interface with the new structure."""
    try:
        from gemini_o1.ui.web_interface import run_web_interface
        run_web_interface()
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("Make sure the gemini_o1 package is in your Python path.")
        sys.exit(1)
    except Exception as e:
        print(f"Error running web interface: {e}")
        sys.exit(1)

def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description="Gemini-O1 Migration Helper")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Guide command
    subparsers.add_parser("guide", help="Show the migration guide")
    
    # CLI command
    subparsers.add_parser("cli", help="Run the CLI interface")
    
    # Web command
    subparsers.add_parser("web", help="Run the web interface")
    
    args = parser.parse_args()
    
    if args.command == "guide" or not args.command:
        print_migration_guide()
    elif args.command == "cli":
        run_cli()
    elif args.command == "web":
        run_web()
    else:
        print("Unknown command. Use 'guide', 'cli', or 'web'.")
        sys.exit(1)

if __name__ == "__main__":
    main()