"""
Command-line interface for the Gemini Network.
"""

import asyncio
import argparse
import logging
import sys
import signal

logger = logging.getLogger(__name__)

class GeminiCLI:
    """
    Command-line interface for interacting with the Gemini Network.
    """
    
    def __init__(self, network):
        """
        Initialize the CLI.
        
        Args:
            network: The GeminiNetwork instance
        """
        self.network = network
        signal.signal(signal.SIGINT, self._handle_shutdown)
        
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown on SIGINT."""
        logger.info("Shutting down gracefully...")
        sys.exit(0)
        
    async def run(self):
        """Run the CLI application."""
        parser = self._create_parser()
        args = parser.parse_args()
        
        if not args.command:
            args.command = "interactive"  # Default to interactive mode
        
        try:
            if args.command == "interactive":
                await self._run_interactive_mode()
            elif args.command == "query":
                await self._run_single_query(args.prompt)
            elif args.command == "list":
                await self._list_instances()
        except Exception as e:
            logger.error(f"A fatal error occurred: {e}")
        finally:
            logger.info("Cleaning up resources...")
            
    def _create_parser(self):
        """Create the argument parser for the CLI."""
        parser = argparse.ArgumentParser(description="Gemini Network Command Line Interface")
        subparsers = parser.add_subparsers(dest="command", help="Commands")
        
        # Interactive mode command
        interactive_parser = subparsers.add_parser("interactive", help="Start interactive mode")
        
        # Single query command
        query_parser = subparsers.add_parser("query", help="Execute a single query")
        query_parser.add_argument("prompt", help="The prompt to send to the Gemini Network")
        
        # List instances command
        list_parser = subparsers.add_parser("list", help="List all active instances")
        
        return parser
        
    async def _run_interactive_mode(self):
        """Run in interactive mode."""
        print("Gemini CLI initialized. Type 'exit' or 'quit' to exit.")
        max_retries = 3
        retry_delay = 1
        
        while True:
            try:
                user_input = input("> ")
                if user_input.lower() in ['exit', 'quit']:
                    break
                    
                for attempt in range(max_retries):
                    try:
                        response = await self.network.handle_user_input(user_input)
                        print(f"Assistant: {response}")
                        break
                    except asyncio.CancelledError:
                        if attempt < max_retries - 1:
                            logger.warning(f"Connection attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            logger.error("Max retries reached. Connection failed.")
                            raise
            except EOFError:
                logger.error("Connection to Gemini API lost. Please check your internet connection and try again.")
                break
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                
    async def _run_single_query(self, prompt):
        """Run a single query and exit."""
        response = await self.network.handle_user_input(prompt)
        print(response)
        
    async def _list_instances(self):
        """List all active instances."""
        instances = await self.network.list_instances()
        print(f"Mother Node: {instances['mother_node']['role']} (ID: {instances['mother_node']['id']})")
        
        if instances['instances']:
            print("\nActive Instances:")
            for idx, instance in enumerate(instances['instances'], 1):
                print(f"{idx}. {instance['role']} (ID: {instance['id']})")
        else:
            print("\nNo active instances.")
            
async def cli_main(network):
    """Main entry point for the CLI application."""
    cli = GeminiCLI(network)
    await cli.run()