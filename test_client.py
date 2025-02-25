#!/usr/bin/env python3
"""
Test client for the Gemini-O1 project.
This script demonstrates using the command-line interface in beep.py.
"""
import sys
import asyncio
import json
import argparse

async def main():
    parser = argparse.ArgumentParser(description="Gemini-O1 Test Client")
    parser.add_argument('--command', type=str, choices=['interactive', 'query', 'list'], 
                        default='interactive', help='Command to execute')
    parser.add_argument('--prompt', type=str, help='Prompt for query command')
    
    args = parser.parse_args()
    
    # Import required modules dynamically to avoid circular imports
    from beep import GeminiNetwork
    
    # Initialize the network
    print("Initializing Gemini Network...")
    network = GeminiNetwork()
    await network._initialize_mother_node()
    print("Network initialized successfully.")
    
    try:
        if args.command == 'interactive':
            print("Starting interactive mode. Type 'exit' to quit.")
            while True:
                user_input = input("> ")
                if user_input.lower() in ['exit', 'quit']:
                    break
                
                response = await network.handle_user_input(user_input)
                print(f"Assistant: {response}")
                
        elif args.command == 'query':
            if not args.prompt:
                print("Error: --prompt is required for query command.")
                return
            
            print(f"Sending query: {args.prompt}")
            response = await network.handle_user_input(args.prompt)
            print(f"Response: {response}")
            
        elif args.command == 'list':
            instances = await network.list_instances()
            print(f"Mother Node: {instances['mother_node']['role']} (ID: {instances['mother_node']['id']})")
            
            if instances['instances']:
                print("\nActive Instances:")
                for idx, instance in enumerate(instances['instances'], 1):
                    print(f"{idx}. {instance['role']} (ID: {instance['id']})")
            else:
                print("\nNo active instances.")
    
    finally:
        # Clean up resources
        print("Cleaning up resources...")
        await network.cleanup_old_instances()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")