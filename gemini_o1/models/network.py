"""
Core GeminiNetwork implementation for managing AI instances.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any

import google.generativeai as genai

from ..models.instance import GeminiInstance
from ..utils.retry import retry_on_exception
from ..utils.prompts import PromptManager
from ..utils.config import config
from ..utils.logging_config import logging_config, PerformanceTracker
from ..commands.command_parser import CommandParser
from ..commands.command_handlers import CommandHandler
from ..communication.response import ResponseGenerator

# Set up logger with request tracking
logger = logging_config.get_logger(__name__)

class GeminiNetwork:
    """
    Central network for coordinating Gemini AI instances.
    
    This class manages the creation, connection, and communication between
    specialized AI instances that collaborate on tasks.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the Gemini Network.
        
        Args:
            api_key: The Gemini API key (optional, will use environment if not provided)
        """
        # Use provided API key or get from config
        self.api_key = api_key or config["GEMINI_API_KEY"]
        if not self.api_key:
            raise ValueError("API key cannot be empty")
        
        # Generate a unique request ID for this network instance
        logging_config.set_request_id()
        logger.info("Initializing Gemini Network")
        
        # Setup components
        self.prompt_manager = PromptManager('prompts.md')
        self.command_parser = CommandParser(self)
        self.command_handler = CommandHandler(self)
        self.response_generator = ResponseGenerator(self)
        
        # Configure Gemini with API key
        genai.configure(api_key=self.api_key)
        
        # Initialize instance storage
        self.instances: Dict[str, GeminiInstance] = {}
        self.mother_node: Optional[GeminiInstance] = None
        self.instance_counter = 0
        
        # Setup rate limiter
        from utils_file import RateLimiter
        rate_limit_config = config.get_rate_limit_config()
        self.rate_limiter = RateLimiter(
            max_calls=rate_limit_config["max_calls"], 
            period=rate_limit_config["period"]
        )
        
    def normalize_instance_id(self, identifier: str) -> str:
        """
        Normalize an instance ID to a consistent format.
        
        Args:
            identifier: The raw instance identifier
            
        Returns:
            Normalized instance ID
        """
        return identifier.replace(" ", "-").lower()
    
    @retry_on_exception()
    async def _initialize_mother_node(self):
        """
        Initialize the mother node (scrum master).
        
        This node coordinates the work of specialized instances.
        """
        logger.info("Initializing mother node")
        perf = PerformanceTracker(logger, "initialize_mother_node")
        perf.start()
        
        mother_prompt = self.prompt_manager.get_prompt('Mother Node Initialization')
        if not mother_prompt:
            raise ValueError("Mother node initialization prompt not found")
        
        self.mother_node = GeminiInstance(
            name="mother_node",
            role="scrum_master",
            model_name=config.get_model_name("normal"),
            instance_id="mother",
            network=self
        )
        
        perf.checkpoint("instance_created")
        
        # Initialize the mother node with system prompt
        await self.get_instance_response(
            self.mother_node, 
            mother_prompt,
            is_system=True
        )
        
        perf.stop(logging.INFO)
        logger.info("Scrum Master Node initialized")
        print("Scrum Master Node initialized")
        
    async def create_instance(
        self, 
        role_description: str,
        model_type: str = "normal",
        initial_prompt: str = "", 
        name: Optional[str] = None, 
        instance_id: Optional[str] = None
    ) -> GeminiInstance:
        """
        Create a new specialized instance.
        
        Args:
            role_description: The role of the instance
            model_type: The model type to use (normal or thinking)
            initial_prompt: Initial prompt to send to the instance
            name: Optional name for the instance
            instance_id: Optional specific ID for the instance
            
        Returns:
            The created GeminiInstance
        """
        logger.info(f"Creating new instance with role: {role_description}")
        perf = PerformanceTracker(logger, "create_instance")
        perf.start()
        
        if name is None:
            name = f"instance_{len(self.instances)}"
        
        model_name = config.get_model_name(model_type)
        
        if instance_id is None:
            self.instance_counter += 1
            instance_id = f"inst_{self.instance_counter}"
            
        instance_id = self.normalize_instance_id(instance_id)
        
        # Create the instance with a unique ID within the request context
        instance_request_id = f"{logging_config.request_id}-{instance_id}"
        logging_config.set_request_id(instance_request_id)
        
        instance = GeminiInstance(
            name=name,
            role=role_description,
            model_name=model_name,
            instance_id=instance_id,
            network=self
        )

        perf.checkpoint("instance_created")
        
        if initial_prompt:
            await self.get_instance_response(instance, initial_prompt, is_system=True)
            perf.checkpoint("initial_prompt_sent")
        
        self.instances[instance.instance_id] = instance
        
        # Restore the previous request ID
        logging_config.set_request_id()
        
        logger.info(f"Instance created: {instance_id} with role {role_description}")
        perf.stop()
        
        return instance
        
    async def cleanup_old_instances(self, max_age_hours: float = 1.0) -> int:
        """
        Remove instances that haven't been used for a while.
        
        Args:
            max_age_hours: Maximum age in hours before removing an instance
            
        Returns:
            Number of instances removed
        """
        logger.info(f"Cleaning up instances older than {max_age_hours} hours")
        
        current_time = time.time()
        to_remove = [
            instance_id for instance_id, instance in self.instances.items()
            if (current_time - instance.created_at) > (max_age_hours * 3600)
        ]
        
        for instance_id in to_remove:
            logger.info(f"Removing old instance: {instance_id}")
            del self.instances[instance_id]
            
        return len(to_remove)
    
    async def get_instance_response(
        self, 
        instance: GeminiInstance, 
        prompt: str,
        is_system: bool = False
    ) -> str:
        """
        Get a response from an instance.
        
        Args:
            instance: The instance to query
            prompt: The prompt to send
            is_system: Whether this is a system message
            
        Returns:
            The response text
        """
        # Set the request ID to include the instance ID
        instance_request_id = f"{logging_config.request_id}-{instance.instance_id}"
        logging_config.set_request_id(instance_request_id)
        
        logger.info(f"Getting response from instance {instance.instance_id}")
        perf = PerformanceTracker(logger, f"instance_response_{instance.instance_id}")
        perf.start()
        
        try:
            response = await self.response_generator.get_instance_response(
                instance,
                prompt,
                is_system
            )
            
            perf.stop()
            
            # Restore the previous request ID
            logging_config.set_request_id()
            
            return response
        except Exception as e:
            logger.error(f"Error getting response from instance {instance.instance_id}: {e}")
            
            # Restore the previous request ID even on error
            logging_config.set_request_id()
            
            raise
        
    async def connect_instances(self, instance1_id: str, instance2_id: str) -> bool:
        """
        Connect two instances to allow direct communication.
        
        Args:
            instance1_id: ID of the first instance
            instance2_id: ID of the second instance
            
        Returns:
            True if connection was successful, False otherwise
        """
        logger.info(f"Connecting instances {instance1_id} <-> {instance2_id}")
        
        if instance1_id in self.instances and instance2_id in self.instances:
            inst1 = self.instances[instance1_id]
            inst2 = self.instances[instance2_id]
            inst1.connected_instances[instance2_id] = inst2
            inst2.connected_instances[instance1_id] = inst1
            return True
            
        logger.warning(f"Failed to connect instances: {instance1_id} or {instance2_id} not found")
        return False
    
    async def verify_all_nodes_complete(self) -> bool:
        """
        Check if all instances have completed their tasks.
        
        Returns:
            True if all instances have completed, False otherwise
        """
        return all(instance.task_completed for instance in self.instances.values())
    
    async def process_mother_node_command(self, response: str) -> Dict:
        """
        Process commands from the mother node.
        
        Args:
            response: The mother node's response text
            
        Returns:
            Result dictionary with actions taken, responses, and new instances
        """
        logger.info(f"Processing mother node command")
        perf = PerformanceTracker(logger, "process_mother_node_command")
        perf.start()
        
        # Log the command to help with debugging
        logger.debug(f"Mother node command: {response}")
        print(f"Mother Node: {response}")
        
        # Parse commands from the response
        commands = self.command_parser.parse_commands(response)
        perf.checkpoint("commands_parsed")
        
        # Process the commands
        result = await self.command_handler.handle_commands(commands)
        perf.checkpoint("commands_processed")
        
        # Log the results for debugging
        logger.info(f"Mother node command processing complete: {len(commands)} commands processed")
        logger.debug(f"Command processing result: {result}")
        
        perf.stop()
        return result
    
    async def synthesize_with_mother_node(self, node_outputs: List[Tuple[str, str]]) -> str:
        """
        Synthesize outputs from multiple instances using the mother node.
        
        Args:
            node_outputs: List of (instance_id, output) tuples
            
        Returns:
            The synthesized response
        """
        logger.info("Synthesizing outputs with mother node")
        perf = PerformanceTracker(logger, "synthesize_with_mother_node")
        perf.start()
        
        all_outputs = []
        for instance in self.instances.values():
            all_outputs.extend(instance.outputs)
        
        # If there are no outputs, provide a detailed description of the interface
        if not all_outputs:
            has_image_content = any("image" in output[1].lower() for output in node_outputs if len(output) > 1)
            
            outputs_text = self._get_default_response(has_image_content)
        else:
            outputs_text = "\n".join(all_outputs)
        
        # Send the synthesis prompt to the mother node
        mother_prompt = self.prompt_manager.get_prompt('Synthesis Prompt', '').format(outputs_text=outputs_text)
        
        perf.checkpoint("prompt_prepared")
        
        # Make sure we're using the mother node's request ID context
        mother_request_id = f"{logging_config.request_id}-mother"
        logging_config.set_request_id(mother_request_id)
        
        response = await self.get_instance_response(self.mother_node, mother_prompt)
        
        # Restore the previous request ID
        logging_config.set_request_id()
        
        perf.stop()
        return response
    
    def _get_default_response(self, has_image_content: bool) -> str:
        """Get a default response description when no outputs are available."""
        if has_image_content:
            return """
            The Gemini-O1 interface is a sophisticated chat application with a dark theme, divided into three main sections:
            
            1. Left Sidebar (Navigation):
               - Contains navigation options including "Chat", "Workflow", and "Settings"
               - The Chat option is currently selected/active
               - There's also a "Templates" section with options
               - Session stats showing nodes active, messages, and API calls
            
            2. Main Content Area (Chat Window):
               - Shows the conversation between the user and the AI
               - User's message with an image is displayed
               - The Scrum Master's response is shown with a "SYNTHESIS" badge
               - Text input field at the bottom with formatting options
            
            3. Right Sidebar (Network Information):
               - Shows "Network Nodes" with filter options
               - Displays activity count and active nodes count
               - Lists active nodes including Scrum Master and specialized nodes
               - System status showing "Online" and update time
            """
        else:
            return """
            The Gemini-O1 interface is a sophisticated chat application with a dark theme, divided into three main sections:
            
            1. Left Sidebar (Navigation):
               - Contains navigation options including "Chat", "Workflow", and "Settings"
               - The Chat option is currently selected/active
               - There's also a "Templates" section with options
               - Session stats showing nodes active, messages, and API calls
            
            2. Main Content Area (Chat Window):
               - Shows the conversation between the user and the AI
               - User's message is displayed
               - The Scrum Master's response is shown with a "SYNTHESIS" badge
               - Text input field at the bottom with formatting options
            
            3. Right Sidebar (Network Information):
               - Shows "Network Nodes" with filter options
               - Displays activity count and active nodes count
               - Lists active nodes including Scrum Master and specialized nodes
               - System status showing "Online" and update time
            """
    
    async def handle_user_input(self, user_input: str) -> str:
        """
        Handle user input and coordinate processing through the network.
        
        Args:
            user_input: The user's input text
            
        Returns:
            The response to the user
        """
        # Generate a new request ID for this user interaction
        logging_config.set_request_id()
        
        logger.info(f"Handling user input: {user_input[:50]}{'...' if len(user_input) > 50 else ''}")
        perf = PerformanceTracker(logger, "handle_user_input")
        perf.start()
        
        if not user_input.strip():
            raise ValueError("User input cannot be empty")

        if user_input.lower() in ['exit', 'quit']:
            return "Goodbye! Thank you for using the system."

        # Log the full input for debugging (might contain sensitive info, so debug level)
        logger.debug(f"Full user input: {user_input}")
        
        # Get context from previous interactions
        last_context = ""
        if self.mother_node.history:
            last_response = self.mother_node.history[-1].get('text', '')
            if last_response:
                last_context = f"\nPrevious response:\n{last_response}\n"
        
        # Prepare the mother node prompt
        mother_prompt = f"""
        User request: {user_input}

        {last_context}
        As a Scrum Master, analyze and break down this request following these EXACT steps:

        1. ANALYZE: Provide clear task analysis
        2. CREATE: Make specialist instances if needed (format: CREATE: role | model_type | responsibility)
           Available model types:
           - normal: Standard model for basic tasks
           - thinking: Enhanced model for complex reasoning
        3. TO: Assign specific tasks to instances (format: TO instance-id: detailed task)
        4. SYNTHESIZE: At the end

        Current team: {[f"{id}: {inst.role}" for id, inst in self.instances.items()]}

        Rules:
        - Must use ANALYZE, CREATE, TO, and SYNTHESIZE commands
        - Each command must be on its own line
        - Keep responses focused and actionable
        - Always delegate tasks using TO commands
        - Specify model_type in CREATE commands
        - End with SYNTHESIZE
        """
        
        perf.checkpoint("prompt_prepared")
        
        try:
            # Get the mother node's analysis and commands
            mother_response = await self.get_instance_response(self.mother_node, mother_prompt)
            if not mother_response:
                logger.warning("No response from mother node. Retrying...")
                return "Sorry, I'm unable to process your request at this time."
            
            perf.checkpoint("mother_node_response")
            
            # Process the mother node's commands
            results = await self.process_mother_node_command(mother_response)
            
            perf.checkpoint("commands_processed")
            
            # If no responses were generated, use a direct command
            if not results['responses']:
                logger.warning("No responses from mother node commands. Using direct command.")
                direct_command = self.prompt_manager.get_prompt('Direct Command Template', '').format(user_input=user_input)
                results = await self.process_mother_node_command(direct_command)
                
                perf.checkpoint("direct_command_processed")

            # Prepare the final response
            final_response = ""
            if 'synthesized' in results['responses']:
                final_response = results['responses']['synthesized']
            elif results['responses']:
                final_response = "\n".join(results['responses'].values())
            else:
                final_response = "I apologize, but I couldn't process your request properly."
                
            perf.stop(logging.INFO)
            
            # Log metrics about this interaction
            metrics = {
                "user_input_length": len(user_input),
                "response_length": len(final_response),
                "instances_created": len(results.get('new_instances', [])),
                "actions_taken": len(results.get('actions_taken', [])),
                "responses_generated": len(results.get('responses', {}))
            }
            logger.info("User interaction metrics", extra={"data": metrics})
                
            return final_response
                
        except Exception as e:
            logger.error(f"Error during mother node communication: {e}")
            return "Sorry, I'm unable to process your request at this time."
    
    async def list_instances(self) -> Dict:
        """
        Get information about all active instances.
        
        Returns:
            Dictionary with mother node and instance information
        """
        logger.info("Listing instances")
        
        return {
            "mother_node": {
                "role": self.mother_node.role,
                "id": self.mother_node.instance_id
            },
            "instances": [
                {
                    "name": inst.name,
                    "role": inst.role,
                    "id": inst.instance_id
                }
                for inst in self.instances.values()
            ]
        }
    
    async def __aenter__(self):
        """Initialize the network when used as a context manager."""
        await self._initialize_mother_node()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting the context manager."""
        await self.cleanup_old_instances()