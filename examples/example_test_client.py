#!/usr/bin/env python3
"""
Test client for Gemini-O1 network

This script demonstrates how to use the improved CLI interface
for the Gemini-O1 network with different modes:
- interactive: Interactive chat session with the network
- query: Execute a single query and exit
- list: List all active instances and exit

Usage:
    python test_client.py interactive
    python test_client.py query "Write a short poem about AI"
    python test_client.py list
"""

import asyncio
import sys
import os
import logging
from typing import Optional, List, Dict

# Add parent directory to path so we can import beep
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from beep import cli_main, GeminiNetwork

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('test_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_client")

async def test_interactive_mode():
    """Test the interactive mode with predefined inputs"""
    # Save original stdin/stdout
    orig_stdin = sys.stdin
    orig_stdout = sys.stdout
    
    try:
        # Create a pipe for stdin simulation
        r, w = os.pipe()
        sys.stdin = os.fdopen(r, 'r')
        
        # Redirect stdout to capture output
        sys.stdout = open('output.txt', 'w')
        
        # Write test inputs to the pipe
        os.write(w, b"Write a short poem about AI\n")
        os.write(w, b"Make it more whimsical\n")
        os.write(w, b"exit\n")
        os.close(w)
        
        # Run the CLI main function with 'interactive' argument
        sys.argv = ['test_client.py', 'interactive']
        await cli_main()
        
    finally:
        # Restore original stdin/stdout
        sys.stdin = orig_stdin
        sys.stdout = orig_stdout
        
    # Print the captured output
    with open('output.txt', 'r') as f:
        print("=== Interactive Mode Test Results ===")
        print(f.read())
    
    # Cleanup
    os.remove('output.txt')

async def test_query_mode(query: str):
    """Test the query mode with a specified prompt"""
    # Save original stdout
    orig_stdout = sys.stdout
    
    try:
        # Redirect stdout to capture output
        sys.stdout = open('output.txt', 'w')
        
        # Run the CLI main function with 'query' argument
        sys.argv = ['test_client.py', 'query', query]
        await cli_main()
        
    finally:
        # Restore original stdout
        sys.stdout = orig_stdout
        
    # Print the captured output
    with open('output.txt', 'r') as f:
        print("=== Query Mode Test Results ===")
        print(f.read())
    
    # Cleanup
    os.remove('output.txt')

async def test_list_mode():
    """Test the list mode to display all active instances"""
    # Save original stdout
    orig_stdout = sys.stdout
    
    try:
        # Redirect stdout to capture output
        sys.stdout = open('output.txt', 'w')
        
        # Run the CLI main function with 'list' argument
        sys.argv = ['test_client.py', 'list']
        await cli_main()
        
    finally:
        # Restore original stdout
        sys.stdout = orig_stdout
        
    # Print the captured output
    with open('output.txt', 'r') as f:
        print("=== List Mode Test Results ===")
        print(f.read())
    
    # Cleanup
    os.remove('output.txt')

async def run_tests():
    """Run all test modes sequentially"""
    print("\n=== Testing List Mode (Before any instances) ===")
    await test_list_mode()
    
    print("\n=== Testing Query Mode ===")
    await test_query_mode("Write a short story about a robot learning to paint")
    
    print("\n=== Testing List Mode (After query) ===")
    await test_list_mode()
    
    print("\n=== Testing Interactive Mode ===")
    await test_interactive_mode()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "interactive":
        asyncio.run(cli_main())
    elif command == "query" and len(sys.argv) > 2:
        # Join all remaining arguments as the query
        query = " ".join(sys.argv[2:])
        asyncio.run(cli_main())
    elif command == "list":
        asyncio.run(cli_main())
    elif command == "run-tests":
        asyncio.run(run_tests())
    else:
        print(__doc__)
        sys.exit(1)