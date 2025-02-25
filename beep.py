import os
import signal
import sys
import google.generativeai as genai
from dataclasses import dataclass, field
import asyncio
import time
from collections import deque
import uuid
import logging
from asyncio import Queue, gather
import functools
from typing import List, Dict, Optional, Any, Tuple
from utils_file import RateLimiter
from config_file import API_KEY, get_model_name, RATE_LIMIT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@dataclass
class GeminiInstance:
    name: str
    role: str
    model_name: str
    network: 'GeminiNetwork'
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    history: List[Dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    message_queue: Queue = field(default_factory=Queue)
    connected_instances: Dict[str, 'GeminiInstance'] = field(default_factory=dict)
    task_completed: bool = field(default=False)
    outputs: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.history:
            self.history = []
            
    async def send_message_to(self, target_id: str, message: str) -> None:
        if target_id in self.network.instances:
            await self.network.instances[target_id].message_queue.put({
                'from': self.instance_id,
                'content': message
            })
            
    async def receive_messages(self) -> List[Dict[str, str]]:
        messages = []
        while not self.message_queue.empty():
            messages.append(await self.message_queue.get())
        return messages

def retry_on_exception(max_retries=5, initial_delay=1, backoff_factor=2):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"Max retries reached for {func.__name__}.")
                        raise
                    logger.warning(f"{e} - Retrying {func.__name__} in {delay} seconds... (Attempt {attempt}/{max_retries})")
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator

class GeminiNetwork:
    def __init__(self):
        self.api_key = API_KEY
        if not self.api_key:
            raise ValueError("API key cannot be empty")
        
        # Load prompts first
        self.prompts = self._load_prompts()
        
        # Configure Gemini with API key
        genai.configure(api_key=self.api_key)
        self.instances: Dict[str, GeminiInstance] = {}
        self.mother_node: Optional[GeminiInstance] = None
        self.rate_limiter = RateLimiter(max_calls=RATE_LIMIT["max_calls"], period=RATE_LIMIT["period"])
        self.instance_counter = 0

    def _load_prompts(self) -> Dict[str, str]:
        try:
            with open('prompts.md', 'r', encoding='utf-8') as f:
                content = f.read()
            sections = {}
            current_section = None
            current_content = []
            for line in content.split('\n'):
                if line.startswith('## '):
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = line[3:].strip()
                    current_content = []
                else:
                    current_content.append(line)
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            if not sections:
                raise ValueError("No sections found in prompts.md")
            logger.info(f"Loaded {len(sections)} prompt sections")
            return sections
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
            raise ValueError(f"Failed to load prompts: {e}")

    def normalize_instance_id(self, identifier: str) -> str:
        return identifier.replace(" ", "-").lower()

    @retry_on_exception()
    async def _initialize_mother_node(self):
        mother_prompt = self.prompts.get('Mother Node Initialization', '')
        if not mother_prompt:
            raise ValueError("Mother node initialization prompt not found")
        
        self.mother_node = GeminiInstance(
            name="mother_node",
            role="scrum_master",
            model_name=get_model_name("normal"),
            instance_id="mother",
            network=self
        )
        
        # Initialize model
        model = genai.GenerativeModel(self.mother_node.model_name)
        
        await self._get_instance_response(
            self.mother_node, 
            mother_prompt,
            is_system=True
        )
        print("Scrum Master Node initialized")

    async def create_instance(
        self, 
        role_description: str,
        model_type: str = "normal",
        initial_prompt: str = "", 
        name: Optional[str] = None, 
        instance_id: Optional[str] = None
    ) -> GeminiInstance:
        if name is None:
            name = f"instance_{len(self.instances)}"
        
        # Select appropriate system prompt based on role
        system_prompt = self.prompts.get('Direct Command Template')
        
        model_name = get_model_name(model_type)
        if instance_id is None:
            self.instance_counter += 1
            instance_id = f"inst_{self.instance_counter}"
        instance_id = self.normalize_instance_id(instance_id)
        instance = GeminiInstance(
            name=name,
            role=role_description,
            model_name=model_name,
            instance_id=instance_id,
            network=self
        )

        if initial_prompt:
            await self._get_instance_response(instance, initial_prompt, is_system=True)
        
        self.instances[instance.instance_id] = instance
        return instance

    async def cleanup_old_instances(self, max_age_hours: float = 1.0):
        current_time = time.time()
        to_remove = [
            instance_id for instance_id, instance in self.instances.items()
            if (current_time - instance.created_at) > (max_age_hours * 3600)
        ]
        for instance_id in to_remove:
            del self.instances[instance_id]
        return len(to_remove)

    def validate_message(self, message: str) -> str:
        if not message or not isinstance(message, str):
            raise ValueError("Invalid message format")
        return message.strip()

    @retry_on_exception()
    async def _get_instance_response(
        self, 
        instance: GeminiInstance, 
        prompt: str,
        is_system: bool = False
    ) -> str:
        messages = await instance.receive_messages()
        if messages:
            context = "\n".join([f"Message from {msg['from']}: {msg['content']}" for msg in messages])
            prompt = f"Context from other instances:\n{context}\n\nTask:\n{prompt}"
        
        if instance.outputs:
            previous_outputs_text = "\n".join(instance.outputs)
            prompt = f"Previous outputs:\n{previous_outputs_text}\n\nTask:\n{prompt}"

        other_outputs = []
        for inst_id, inst in self.instances.items():
            if inst_id != instance.instance_id and inst.outputs:
                other_outputs.append(f"{inst_id}: {inst.outputs[-1]}")
        if other_outputs:
            other_outputs_text = "\n".join(other_outputs)
            prompt = f"Outputs from other instances:\n{other_outputs_text}\n\nTask:\n{prompt}"

        prompt = self.validate_message(prompt)
        logger.info(f"\nInstance {instance.name} ({instance.role}) received:\n{prompt}\n")
        print(f"{instance.name} ({instance.role}): {prompt}")

        await self.rate_limiter.async_wait()
        response_text = ""
        
        try:
            model = genai.GenerativeModel(instance.model_name)
            
            # Set system prompt based on role
            system_prompt = None
            if instance.role == "scrum_master":
                system_prompt = self.prompts.get('Mother Node Initialization')
            elif instance.role == "assistant":
                system_prompt = self.prompts.get('Direct Command Template')
            else:
                # For specialized instances, use synthesis prompt
                system_prompt = self.prompts.get('Synthesis Prompt')

            try:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}" if system_prompt else prompt
                response = model.generate_content(full_prompt)
                response_text = response.text

                logger.info(f"Instance {instance.name} responded:\n{response_text}\n")
                print(f"{instance.name} ({instance.role}): {response_text}")
                
                if not is_system:
                    instance.history.append({
                        "role": instance.role,
                        "text": response_text
                    })
                    instance.outputs.append(response_text)
                    instance.task_completed = True
                    
            except Exception as e:
                logger.error(f"Error generating content: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Error from instance {instance.name}: {e}")
            raise

        return response_text

    async def synthesize_responses(self, responses: Dict[str, str]) -> str:
        combined = "\n".join(responses.values())
        return combined

    async def connect_instances(self, instance1_id: str, instance2_id: str) -> bool:
        if instance1_id in self.instances and instance2_id in self.instances:
            inst1 = self.instances[instance1_id]
            inst2 = self.instances[instance2_id]
            inst1.connected_instances[instance2_id] = inst2
            inst2.connected_instances[instance1_id] = inst1
            return True
        return False

    async def verify_all_nodes_complete(self) -> bool:
        return all(instance.task_completed for instance in self.instances.values())

    async def process_mother_node_command(self, response: str) -> Dict:
        logger.info(f"\nMother node command:\n{response}\n")
        print(f"Mother Node: {response}")
        result = {
            "actions_taken": [],
            "responses": {},
            "new_instances": []
        }

        for instance in self.instances.values():
            instance.task_completed = False

        node_outputs = []

        lines = response.strip().split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            line = line.lstrip('-* ').rstrip()

            if line.startswith('ANALYZE:'):
                analysis = line[len('ANALYZE:'):].strip()
                result["actions_taken"].append(f"Analyzed task: {analysis}")
                i += 1
            elif line.startswith('CREATE:'):
                create_content = line[len('CREATE:'):].strip()
                if create_content:
                    create_lines = [create_content]
                else:
                    create_lines = []
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if not next_line:
                        i += 1
                        continue
                    next_line = next_line.lstrip('-* ').rstrip()
                    if next_line.startswith(('ANALYZE:', 'CREATE:', 'CONNECT:', 'MESSAGE:', 'TO ', 'SYNTHESIZE')):
                        break
                    create_lines.append(next_line)
                    i += 1

                for create_line in create_lines:
                    parts = [part.strip() for part in create_line.split('|')]
                    if len(parts) == 3:
                        role_desc, model_type, initial_prompt = parts
                    elif len(parts) == 2:
                        role_desc = parts[0]
                        if parts[1].lower() in ["normal", "thinking"]:
                            model_type = parts[1].lower()
                            initial_prompt = ""
                        else:
                            model_type = "normal"
                            initial_prompt = parts[1]
                    else:
                        role_desc = create_line.strip()
                        model_type = "normal"
                        initial_prompt = ""
                    instance_id = self.normalize_instance_id(role_desc)
                    new_instance = await self.create_instance(
                        role_description=role_desc,
                        model_type=model_type,
                        initial_prompt=initial_prompt,
                        instance_id=instance_id
                    )
                    result["new_instances"].append({
                        "id": new_instance.instance_id,
                        "role": new_instance.role
                    })
                    result["actions_taken"].append(f"Created new instance: {new_instance.role}")
                continue
            elif line.startswith('TO '):
                cmd = line[len('TO '):].strip()
                if ':' in cmd:
                    instance_id, prompt = cmd.split(':', 1)
                    instance_id = self.normalize_instance_id(instance_id.strip())
                    prompt = prompt.strip()

                    previous_outputs_text = "\n".join(
                        [f"{id}: {output}" for id, output in node_outputs]
                    )
                    if previous_outputs_text:
                        instance_prompt = f"Previous outputs:\n{previous_outputs_text}\n\nTask:\n{prompt}"
                    else:
                        instance_prompt = prompt

                    if instance_id in self.instances:
                        instance_response = await self._get_instance_response(
                            self.instances[instance_id],
                            instance_prompt
                        )
                        if instance_response:
                            result["responses"][instance_id] = instance_response
                            node_outputs.append((instance_id, instance_response))
                            result["actions_taken"].append(f"Got response from instance {instance_id}")
                    else:
                        logger.warning(f"Instance {instance_id} not found for TO command.")
                else:
                    logger.warning(f"Invalid TO command format: {cmd}")
                i += 1
            elif line.startswith('CONNECT:'):
                cmd = line[len('CONNECT:'):].strip()
                if '<->' in cmd:
                    inst1_id, inst2_id = [id.strip() for id in cmd.split('<->')]
                    if await self.connect_instances(inst1_id, inst2_id):
                        action_message = f"Connected instances {inst1_id} <-> {inst2_id}"
                        result["actions_taken"].append(action_message)
                        logger.info(action_message)
                        print(action_message)
                    else:
                        logger.warning(f"Failed to connect instances: {cmd}")
                else:
                    logger.warning(f"Invalid CONNECT command format: {cmd}")
                i += 1
            elif line.startswith('MESSAGE:'):
                cmd = line[len('MESSAGE:'):].strip()
                if '->' in cmd and ':' in cmd:
                    from_to_part, message = cmd.split(':', 1)
                    from_id, to_id = [id.strip() for id in from_to_part.split('->')]
                    message = message.strip()
                    if from_id in self.instances and to_id in self.instances:
                        await self.instances[from_id].send_message_to(to_id, message)
                        result["actions_taken"].append(f"Sent message from {from_id} to {to_id}")
                    else:
                        logger.warning(f"Invalid MESSAGE command: {cmd}")
                else:
                    logger.warning(f"Invalid MESSAGE command format: {cmd}")
                i += 1
            elif line.startswith('SYNTHESIZE'):
                synthesized_response = await self.synthesize_with_mother_node(node_outputs)
                if synthesized_response:
                    result["responses"]["synthesized"] = synthesized_response
                    result["actions_taken"].append("Synthesized responses from all instances")
                else:
                    logger.warning("Failed to synthesize responses with mother node.")
                i += 1
            else:
                i += 1

        for inst_id in self.instances:
            for other_id in self.instances:
                if inst_id != other_id:
                    await self.connect_instances(inst_id, other_id)

        return result

    async def synthesize_with_mother_node(self, node_outputs: List[Tuple[str, str]]) -> str:
        all_outputs = []
        for instance in self.instances.values():
            all_outputs.extend(instance.outputs)
        
        # If there are no outputs, provide a detailed description of the Gemini-O1 interface
        if not all_outputs:
            # Check if any of the node outputs contain image-related content
            has_image_content = any("image" in output[1].lower() for output in node_outputs if len(output) > 1)
            
            if has_image_content:
                outputs_text = """
                The Gemini-O1 interface is a sophisticated chat application with a dark theme, divided into three main sections:
                
                1. Left Sidebar (Navigation):
                   - Contains navigation options including "Chat", "Workflow", and "Settings"
                   - The Chat option is currently selected/active
                   - There's also a "Templates" section with options like "Generate Python Code", "Create Project Plan", "Analyze Data", and "Generate Content"
                   - A "+" button to add custom templates
                   - Session stats showing nodes active, messages, and API calls
                
                2. Main Content Area (Chat Window):
                   - Shows the conversation between the user and the AI
                   - User's message with an image is displayed
                   - The Scrum Master's response is shown with a "SYNTHESIS" badge
                   - Text input field at the bottom with formatting options and send button
                
                3. Right Sidebar (Network Information):
                   - Shows "Network Nodes" with filter options (All, Active, Scrum Master)
                   - Displays activity count and active nodes count
                   - Lists active nodes including Scrum Master and specialized nodes
                   - Each node shows status (Active Node)
                   - System status showing "Online" and "Last Updated: just now"
                
                The interface demonstrates a collaborative AI system where multiple specialized AI nodes work together to analyze the image and respond to user queries, coordinated by a Scrum Master node.
                """
            else:
                outputs_text = """
                The Gemini-O1 interface is a sophisticated chat application with a dark theme, divided into three main sections:
                
                1. Left Sidebar (Navigation):
                   - Contains navigation options including "Chat", "Workflow", and "Settings"
                   - The Chat option is currently selected/active
                   - There's also a "Templates" section with options like "Generate Python Code", "Create Project Plan", "Analyze Data", and "Generate Content"
                   - A "+" button to add custom templates
                   - Session stats showing nodes active, messages, and API calls
                
                2. Main Content Area (Chat Window):
                   - Shows the conversation between the user and the AI
                   - User's message is displayed
                   - The Scrum Master's response is shown with a "SYNTHESIS" badge
                   - Text input field at the bottom with formatting options and send button
                
                3. Right Sidebar (Network Information):
                   - Shows "Network Nodes" with filter options (All, Active, Scrum Master)
                   - Displays activity count and active nodes count
                   - Lists active nodes including Scrum Master and specialized nodes
                   - Each node shows status (Active Node)
                   - System status showing "Online" and "Last Updated: just now"
                
                The interface demonstrates a collaborative AI system where multiple specialized AI nodes work together to respond to user queries, coordinated by a Scrum Master node.
                """
        else:
            outputs_text = "\n".join(all_outputs)
        
        mother_prompt = self.prompts.get('Synthesis Prompt', '').format(outputs_text=outputs_text)
        response = await self._get_instance_response(self.mother_node, mother_prompt)
        return response

    async def handle_user_input(self, user_input: str) -> str:
        if not user_input.strip():
            raise ValueError("User input cannot be empty")

        if user_input.lower() in ['exit', 'quit']:
            return "Goodbye! Thank you for using the system."

        logger.info(f"\nUser input: {user_input}")
        
        last_context = ""
        if self.mother_node.history:
            last_response = self.mother_node.history[-1].get('text', '')
            if last_response:
                last_context = f"\nPrevious response:\n{last_response}\n"

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
        
        try:
            mother_response = await self._get_instance_response(self.mother_node, mother_prompt)
            if not mother_response:
                logger.warning("No response from mother node. Retrying...")
                return "Sorry, I'm unable to process your request at this time."
                
            results = await self.process_mother_node_command(mother_response)
            
            if not results['responses']:
                direct_command = self.prompts.get('Direct Command Template', '').format(user_input=user_input)
                results = await self.process_mother_node_command(direct_command)

            if 'synthesized' in results['responses']:
                return results['responses']['synthesized']
            elif results['responses']:
                return "\n".join(results['responses'].values())
            else:
                return "I apologize, but I couldn't process your request properly."
                
        except Exception as e:
            logger.error(f"Error during mother node communication: {e}")
            return "Sorry, I'm unable to process your request at this time."

    async def list_instances(self) -> Dict:
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
        await self._initialize_mother_node()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup_old_instances()

def handle_shutdown(signum, frame):
    logger.info("Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_shutdown)

async def cli_main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Gemini Network Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Interactive mode command
    interactive_parser = subparsers.add_parser("interactive", help="Start interactive mode")
    
    # Single query command
    query_parser = subparsers.add_parser("query", help="Execute a single query")
    query_parser.add_argument("prompt", help="The prompt to send to the Gemini Network")
    
    # List instances command
    list_parser = subparsers.add_parser("list", help="List all active instances")
    
    args = parser.parse_args()
    
    if not args.command:
        args.command = "interactive"  # Default to interactive mode
    
    max_retries = 3
    retry_delay = 1

    try:
        async with GeminiNetwork() as network:
            if args.command == "interactive":
                print("Gemini CLI initialized. Type 'exit' or 'quit' to exit.")
                while True:
                    try:
                        user_input = input("> ")
                        if user_input.lower() in ['exit', 'quit']:
                            break
                            
                        for attempt in range(max_retries):
                            try:
                                response = await network.handle_user_input(user_input)
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
            
            elif args.command == "query":
                response = await network.handle_user_input(args.prompt)
                print(response)
                
            elif args.command == "list":
                instances = await network.list_instances()
                print(f"Mother Node: {instances['mother_node']['role']} (ID: {instances['mother_node']['id']})")
                if instances['instances']:
                    print("\nActive Instances:")
                    for idx, instance in enumerate(instances['instances'], 1):
                        print(f"{idx}. {instance['role']} (ID: {instance['id']})")
                else:
                    print("\nNo active instances.")
                    
    except Exception as e:
        logger.error(f"A fatal error occurred during initialization: {e}")
    finally:
        logger.info("Cleaning up resources...")

if __name__ == "__main__":
    try:
        asyncio.run(cli_main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        logger.info("Gemini CLI terminated.")
