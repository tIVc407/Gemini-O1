# pylint: disable=E0401,E1101
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, mock_open, MagicMock
import google.api_core.exceptions
import time
import logging
from beep import GeminiNetwork, GeminiInstance, RateLimiter

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@pytest_asyncio.fixture
async def network():
    """Create a network instance for testing."""
    api_key = "test-api-key"  # Use a dummy API key for testing
    with patch("builtins.open", mock_open(read_data="""
## Mother Node Initialization
Test prompt

## Direct Command Template
Test prompt

## Synthesis Prompt
Test prompt
""")):
        network = GeminiNetwork()
        network.rate_limiter = RateLimiter(max_calls=5, period=60)
        await network.rate_limiter.async_wait()  # Initialize rate limiter
        
        # Mock genai configuration and API calls
        with patch('google.generativeai.GenerativeModel') as mock_model_class, \
             patch.object(network, '_get_instance_response', new_callable=AsyncMock) as mock_get_response:
            mock_model = mock_model_class.return_value
            mock_model.generate_content.return_value.text = "Initialized"
            mock_get_response.return_value = "Initialized"
            await network._initialize_mother_node()
            yield network

class TestGeminiNetwork:
    """Tests for the GeminiNetwork."""
    
    @pytest.mark.asyncio
    async def test_instance_creation(self, network):
        """Test creating a new instance."""
        with patch.object(network, '_get_instance_response', new_callable=AsyncMock) as mock_response:
            mock_response.return_value = "Instance initialized"
            await network.rate_limiter.async_wait()
            instance = await network.create_instance("test-role")
            assert isinstance(instance, GeminiInstance)
            assert instance.role == "test-role"
            assert instance.instance_id in network.instances

    @pytest.mark.asyncio
    async def test_error_handling_empty_input(self, network):
        """Test handling of empty user input."""
        with pytest.raises(ValueError, match="User input cannot be empty"):
            await network.handle_user_input("")

    @pytest.mark.asyncio
    async def test_mother_node_initialization(self, network):
        assert network.mother_node is not None
        assert isinstance(network.mother_node, GeminiInstance)
        assert network.mother_node.role == "scrum_master"

    @pytest.mark.asyncio
    async def test_handle_user_input(self, network):
        test_input = "Write a test story"
        mock_story = "This is a test story response"

        # Mock necessary components
        with patch.object(network, '_get_instance_response', return_value="ANALYZE: Test\nTO writer: Write a story\nSYNTHESIZE"), \
             patch.object(network, 'process_mother_node_command', return_value={
                 "responses": {"writer": mock_story, "synthesized": mock_story},
                 "actions_taken": [],
                 "new_instances": []
             }):
            response = await network.handle_user_input(test_input)
            assert isinstance(response, str)
            assert len(response) > 0
            assert mock_story in response
