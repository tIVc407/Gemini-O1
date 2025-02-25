# pylint: disable=E0401,E1101
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, mock_open, MagicMock
import google.api_core.exceptions
import time
import logging
import os
from typing import Dict

# Configure test logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Mock configuration objects before imports
mock_config = MagicMock()
mock_config.__getitem__.return_value = "dummy-api-key"
mock_config.get.return_value = "dummy-value"
mock_config.get_log_level.return_value = logging.INFO
mock_config.get_model_name.return_value = "gemini-1.5-flash"
mock_config.get_rate_limit_config.return_value = {"max_calls": 15, "period": 60}

mock_logger = MagicMock()
mock_logging_config = MagicMock()
mock_logging_config.get_logger.return_value = mock_logger
mock_logging_config.request_id = "test-request-id"
mock_logging_config.set_request_id.return_value = None

mock_perf_tracker = MagicMock()
mock_perf_tracker.start.return_value = None
mock_perf_tracker.stop.return_value = None
mock_perf_tracker.checkpoint.return_value = None

# Apply mocks using patch decorators
@patch('gemini_o1.utils.config.config', mock_config)
@patch('gemini_o1.utils.logging_config.logging_config', mock_logging_config)
@patch('gemini_o1.utils.logging_config.PerformanceTracker', return_value=mock_perf_tracker)
class TestGeminiNetwork:
    """Tests for the GeminiNetwork."""
    
    from gemini_o1.models.network import GeminiNetwork
    from gemini_o1.models.instance import GeminiInstance
    from utils_file import RateLimiter

    # Configure pytest-asyncio
    def pytest_configure(config):
        config.addinivalue_line("asyncio_mode", "strict")
        config.addinivalue_line("asyncio_fixture_loop_scope", "function")

    @pytest_asyncio.fixture
    async def network(self):
        """Create a network instance for testing."""
        api_key = "test-api-key"  # Use a dummy API key for testing
        
        # Mock the prompt loading
        with patch("gemini_o1.utils.prompts.PromptManager._load_prompts") as mock_load_prompts:
            mock_load_prompts.return_value = {
                "Mother Node Initialization": "Test prompt for mother node",
                "Direct Command Template": "Test prompt for direct commands",
                "Synthesis Prompt": "Test prompt for synthesis"
            }
            
            # Mock genai configuration
            with patch("gemini_o1.models.network.genai.configure"):
                network = self.GeminiNetwork(api_key)
                network.rate_limiter = self.RateLimiter(max_calls=5, period=60)
                
                # Mock the response generation to prevent real API calls
                with patch.object(network.response_generator, 'get_instance_response', new_callable=AsyncMock) as mock_response:
                    mock_response.return_value = "Initialized"
                    await network._initialize_mother_node()
                    yield network

    @pytest.mark.asyncio
    async def test_instance_creation(self, network):
        """Test creating a new instance."""
        # No need to wait for rate limiter in tests
        # Mock the response generator
        with patch.object(network.response_generator, 'get_instance_response', new_callable=AsyncMock) as mock_response:
            mock_response.return_value = "Instance initialized"
            
            instance = await network.create_instance("test-role")
            assert isinstance(instance, self.GeminiInstance)
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
        assert isinstance(network.mother_node, self.GeminiInstance)
        assert network.mother_node.role == "scrum_master"

    @pytest.mark.asyncio
    async def test_handle_user_input(self, network):
        test_input = "Write a test story"
        mock_story = "This is a test story response"

        # Mock necessary components
        with patch.object(network.response_generator, 'get_instance_response', return_value=mock_story), \
             patch.object(network, 'process_mother_node_command', return_value={
                 "responses": {"synthesized": mock_story},
                 "actions_taken": ["Action 1"],
                 "new_instances": []
             }):
            response = await network.handle_user_input(test_input)
            assert isinstance(response, str)
            assert mock_story in response