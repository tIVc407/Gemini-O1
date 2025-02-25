#!/usr/bin/env python3
"""
Simple test to check if key components of the refactored code are working.
"""

import asyncio
import os
import sys

# Set test environment variable to bypass API key validation
os.environ["PYTEST_CURRENT_TEST"] = "1"

# Add the parent directory to the path so we can import gemini_o1
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from gemini_o1 import GeminiNetwork
from gemini_o1.utils.logging_config import logging_config
from unittest.mock import patch, AsyncMock

async def main():
    """Run a simple test."""
    print("Setting up logging...")
    logging_config.setup_logging(enable_console=True)
    
    print("Creating network...")
    with patch("gemini_o1.utils.prompts.PromptManager._load_prompts") as mock_load_prompts:
        mock_load_prompts.return_value = {
            "Mother Node Initialization": "Test prompt for mother node",
            "Direct Command Template": "Test prompt for direct commands",
            "Synthesis Prompt": "Test prompt for synthesis"
        }
        
        with patch("gemini_o1.models.network.genai.configure"):
            # Create a network instance
            network = GeminiNetwork("dummy-api-key")
            
            # Mock the get_instance_response method
            with patch.object(network.response_generator, 'get_instance_response', new_callable=AsyncMock) as mock_response:
                mock_response.return_value = "Initialized"
                
                print("Initializing mother node...")
                await network._initialize_mother_node()
                
                print("Mother node initialized successfully")
                print(f"Request ID: {logging_config.request_id}")
                
                # Test creating an instance
                mock_response.return_value = "Instance created"
                
                print("Creating test instance...")
                instance = await network.create_instance("test-role")
                
                print(f"Instance created with ID: {instance.instance_id}")
                
                # All tests passed
                print("All tests passed!")
                
if __name__ == "__main__":
    asyncio.run(main())