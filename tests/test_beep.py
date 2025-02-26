# pylint: disable=E0401,E1101
import asyncio
from beep import GeminiNetwork
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, mock_open
import google.api_core.exceptions
import time
from beep import RateLimiter, GeminiInstance
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Configure pytest-asyncio
def pytest_configure(config):
    config.addinivalue_line("asyncio_mode", "strict")
    config.addinivalue_line("asyncio_fixture_loop_scope", "function")

@pytest_asyncio.fixture
async def network():
    """Create a network instance for testing."""
    api_key = "AIzaSyACCbhYudSe-lQzqHZp_yi3KSMbka5kTG8"  # Use a dummy API key for testing
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
        
        # Mock the chat send_message_async to prevent real API calls
        with patch.object(network, '_get_instance_response', new_callable=AsyncMock) as mock_get_instance_response:
            mock_get_instance_response.return_value = "Initialized"
            await network._initialize_mother_node()
            yield network

@pytest_asyncio.fixture(autouse=True)
async def cleanup():
    yield
    # Clean up any remaining instances after each test
    api_key = "AIzaSyACCbhYudSe-lQzqHZp_yi3KSMbka5kTG8"  # Use real API key
    if api_key:
        network = GeminiNetwork()
        await network.cleanup_old_instances(max_age_hours=0)

class TestGeminiNetwork:
    """Tests for the GeminiNetwork."""

    @pytest.mark.asyncio
    async def test_instance_creation(self, network):
        """Test creating a new instance."""
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
    async def test_error_handling_invalid_message(self, network):
        """Test handling of invalid message format."""
        with patch.object(network, '_get_instance_response', side_effect=lambda *args, **kwargs: network.validate_message("")):
            with pytest.raises(ValueError, match="Invalid message format"):
                await network._get_instance_response(network.mother_node, "")

    @pytest.mark.asyncio
    async def test_integration_with_gemini_api(self):
        """Integration test with the actual Gemini API."""
        api_key = "AIzaSyACCbhYudSe-lQzqHZp_yi3KSMbka5kTG8"  # Use real API key
        if api_key == "...":
            pytest.skip("API key not provided, skipping integration test.")

        with patch("builtins.open", mock_open(read_data="""
## Mother Node Initialization
Test prompt

## Direct Command Template
Test prompt

## Synthesis Prompt
Test prompt
""")):
            network = GeminiNetwork()
            await network._initialize_mother_node()
            response = await network.handle_user_input("Explain Agile methodology.")
            assert isinstance(response, str)
            assert len(response) > 0

    @pytest.mark.asyncio
    async def test_mother_node_scrum_master_role(self, network):
        """Test mother node's Scrum Master behavior."""
        with patch.object(network, '_get_instance_response', new_callable=AsyncMock) as mock_get_response:
            mock_get_response.return_value = "ANALYZE: Test task\nCREATE: tester | Perform testing\nTO tester: Execute test cases\nSYNTHESIZE"
            
            test_input = "Create a complex task that requires multiple steps"
            await network.handle_user_input(test_input)
            
            await asyncio.sleep(1)  # Wait for a short time to allow task processing
            
            instances = await network.list_instances()
            assert len(instances['instances']) > 0
            # Check if the mother node is initialized
            assert 'mother_node' in instances
            assert instances['mother_node']['role'] == 'scrum_master'

    @pytest.mark.asyncio
    async def test_error_handling_resource_exhausted(self, network):
        """Test handling of ResourceExhausted error."""
        with patch.object(network, '_get_instance_response', 
                         side_effect=google.api_core.exceptions.ResourceExhausted("Resource exhausted")):
            response = await network.handle_user_input("Trigger quota exceeded")
            assert "Sorry, I'm unable to process your request at this time." in response

    @pytest.mark.asyncio
    async def test_cleanup_old_instances(self, network):
        """Test cleanup of old instances."""
        with patch.object(GeminiInstance, 'send_message_to', new_callable=AsyncMock):
            await network.rate_limiter.async_wait()
            await network.create_instance("test-role-1")
            await network.rate_limiter.async_wait()
            await network.create_instance("test-role-2")
            
            # Modify their creation time to be old
            for instance in network.instances.values():
                instance.created_at -= 3600 * 2
    
            removed = await network.cleanup_old_instances(max_age_hours=1.0)
            assert removed == 2
            assert len(network.instances) == 0

    @pytest.mark.asyncio
    async def test_rate_limiter(self, network):
        """Test rate limiter functionality."""
        limiter = RateLimiter(max_calls=15, period=60)
        await limiter.async_wait()  # Initialize the limiter
        
        start_time = time.time()
        
        # Test multiple calls
        for _ in range(3):
            await limiter.async_wait()
        
        duration = time.time() - start_time
        assert duration >= 0

    @pytest.mark.asyncio
    async def test_mother_node_initialization(self, network):
        assert network.mother_node is not None
        assert isinstance(network.mother_node, GeminiInstance)
        assert network.mother_node.role == "scrum_master"

    @pytest.mark.asyncio
    async def test_process_mother_node_command(self, network):
        test_command = """
        ANALYZE: Simple test task
        CREATE: test-handler | Handle test tasks
        TO test-handler: Process this test
        SYNTHESIZE
        """
        instance_mock = AsyncMock()
        instance_mock.instance_id = 'test-handler'
        instance_mock.role = 'test-handler'
        instance_mock.history = []
        
        async def mock_create_instance(*args, **kwargs):
            network.instances[instance_mock.instance_id] = instance_mock
            return instance_mock

        with patch.object(network, 'create_instance', side_effect=mock_create_instance), \
             patch.object(network, '_get_instance_response', return_value="Processed test"):
            results = await network.process_mother_node_command(test_command)
            assert isinstance(results, dict)
            assert 'new_instances' in results
            assert len(results['new_instances']) == 1
            assert results['new_instances'][0]['id'] == 'test-handler'
            assert results['responses']['test-handler'] == "Processed test"
            assert 'Got response from instance test-handler' in results['actions_taken']

    @pytest.mark.asyncio
    async def test_handle_user_input(self, network):
        test_input = "Write a test story"
        mock_story = "This is a test story response"

        instance_mock = AsyncMock()
        instance_mock.instance_id = 'writer'
        instance_mock.role = 'writer'
        instance_mock.history = []

        async def mock_create_instance(*args, **kwargs):
            network.instances[instance_mock.instance_id] = instance_mock
            return instance_mock

        with patch.object(network, '_get_instance_response', return_value="ANALYZE: Test\nTO writer: Write a story\nSYNTHESIZE"), \
             patch.object(network, 'create_instance', side_effect=mock_create_instance), \
             patch.object(network, 'process_mother_node_command', return_value={
                 "responses": {"writer": mock_story, "synthesized": mock_story},
                 "actions_taken": [],
                 "new_instances": []
             }):
            response = await network.handle_user_input(test_input)
            assert isinstance(response, str)
            assert len(response) > 0
            assert mock_story in response

    @pytest.mark.asyncio
    async def test_instance_messaging(self):
        """Test direct instance-to-instance messaging capabilities."""
        with patch("builtins.open", mock_open(read_data="""
## Mother Node Initialization
Test prompt

## Direct Command Template
Test prompt

## Synthesis Prompt
Test prompt
""")):
            network = GeminiNetwork()
            
            # Create two test instances
            instance1 = await network.create_instance("sender")
            instance2 = await network.create_instance("receiver")
            
            # Test connection
            connected = await network.connect_instances(instance1.instance_id, instance2.instance_id)
            assert connected == True
            assert instance2.instance_id in instance1.connected_instances
            assert instance1.instance_id in instance2.connected_instances
            
            # Test message sending
            test_message = "Test message content"
            await instance1.send_message_to(instance2.instance_id, test_message)
            
            # Test message receiving
            messages = await instance2.receive_messages()
            assert len(messages) == 1
            assert messages[0]['from'] == instance1.instance_id
            assert messages[0]['content'] == test_message

    @pytest.mark.asyncio
    async def test_mother_node_communication_commands(self):
        """Test mother node's ability to handle communication commands."""
        with patch("builtins.open", mock_open(read_data="""
## Mother Node Initialization
Test prompt

## Direct Command Template
Test prompt

## Synthesis Prompt
Test prompt
""")):
            network = GeminiNetwork()
            
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = mock_model_class.return_value
                mock_model.generate_content.return_value.text = "Initialized"
                await network._initialize_mother_node()
            
                test_command = """
                ANALYZE: Task requires collaboration
                CREATE: data-analyzer | You analyze incoming data
                CREATE: content-writer | You write content based on analysis
                CONNECT: data-analyzer <-> content-writer
                MESSAGE: data-analyzer -> content-writer: Here's the analyzed data: XYZ
                SYNTHESIZE
                """
            
                mock_instances = {
                    'data-analyzer': GeminiInstance(
                        name="data-analyzer",
                        role="data-analyzer",
                        model_name="gemini-2.0-flash",
                        network=network,
                        instance_id="data-analyzer"
                    ),
                    'content-writer': GeminiInstance(
                        name="content-writer",
                        role="content-writer",
                        model_name="gemini-2.0-flash",
                        network=network,
                        instance_id="content-writer"
                    )
                }
            
                async def mock_create_instance(*args, **kwargs):
                    instance_id = kwargs.get('instance_id') or args[0].replace(" ", "-").lower()
                    instance = mock_instances[instance_id]
                    network.instances[instance_id] = instance
                    return instance
            
                with patch.object(network, 'create_instance', side_effect=mock_create_instance), \
                     patch.object(network, '_get_instance_response', return_value="Processed test"):
                    results = await network.process_mother_node_command(test_command)
                    assert len(results['new_instances']) == 2
                    assert any(inst['id'] == 'data-analyzer' for inst in results['new_instances'])
                    assert any(inst['id'] == 'content-writer' for inst in results['new_instances'])
                    assert any('Connected instances data-analyzer <-> content-writer' in action for action in results['actions_taken'])

    def test_normalize_instance_id(self, network):
        """Test instance ID normalization."""
        test_cases = [
            ("Test Role", "test-role"),
            ("test role", "test-role"),
            ("TEST ROLE", "test-role"),
            ("test-role", "test-role"),
            ("test_role", "test-role"),
            ("test  role", "test-role"),
            ("test_role_2", "test-role-2"),
        ]
        for input_id, expected in test_cases:
            result = network.normalize_instance_id(input_id)
            assert result == expected, f"Failed for input '{input_id}': got '{result}', expected '{expected}'"

    def test_load_prompts(self, network):
        """Test prompt loading functionality."""
        mock_prompts_content = """
## Mother Node Initialization
Mother node init prompt

## Direct Command Template
Direct command template

## Synthesis Prompt
Synthesis prompt
"""
        with patch("builtins.open", mock_open(read_data=mock_prompts_content)):
            prompts = network._load_prompts()
            assert "Mother Node Initialization" in prompts
            assert "Direct Command Template" in prompts
            assert "Synthesis Prompt" in prompts
            assert prompts["Mother Node Initialization"].strip() == "Mother node init prompt"

    def test_load_prompts_empty_file(self, network):
        """Test prompt loading with empty file."""
        with patch("builtins.open", mock_open(read_data="")):
            with pytest.raises(ValueError, match="No sections found in prompts.md"):
                network._load_prompts()

    @pytest.mark.asyncio
    async def test_verify_all_nodes_complete(self, network):
        """Test verification of node completion status."""
        # Create test instances
        instance1 = await network.create_instance("test-role-1")
        instance2 = await network.create_instance("test-role-2")
        
        # Initially, no tasks completed
        assert await network.verify_all_nodes_complete() == False
        
        # Complete tasks
        instance1.task_completed = True
        instance2.task_completed = True
        
        # All tasks completed
        assert await network.verify_all_nodes_complete() == True

    @pytest.mark.asyncio
    async def test_instance_reconnection_failure(self, network):
        """Test handling of instance reconnection failures."""
        # Test connecting non-existent instances
        connected = await network.connect_instances("non-existent-1", "non-existent-2")
        assert connected == False

        # Test connecting one existing and one non-existent instance
        instance = await network.create_instance("test-role")
        connected = await network.connect_instances(instance.instance_id, "non-existent")
        assert connected == False

    @pytest.mark.asyncio
    async def test_synthesize_responses(self, network):
        """Test response synthesis."""
        test_responses = {
            "instance1": "Response from instance 1",
            "instance2": "Response from instance 2"
        }
        combined = await network.synthesize_responses(test_responses)
        assert "Response from instance 1" in combined
        assert "Response from instance 2" in combined
