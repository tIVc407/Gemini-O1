import os
import google.generativeai as genai
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
import asyncio
import time
from collections import deque
import uuid
import logging
from asyncio import Queue, gather
import functools
import google.api_core.exceptions

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
    chat: Any
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    history: List[Dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    message_queue: Queue = field(default_factory=Queue)
    connected_instances: Dict[str, 'GeminiInstance'] = field(default_factory=dict)
    task_completed: bool = field(default=False)
    
    def __post_init__(self):
        if not self.history:
            self.history = []

    async def send_message_to(self, target_id: str, message: str) -> None:
        """Send message to another instance."""
        if target_id in self.connected_instances:
            await self.connected_instances[target_id].message_queue.put({
                'from': self.instance_id,
                'content': message
            })
            
    async def receive_messages(self) -> List[Dict[str, str]]:
        """Retrieve all pending messages."""
        messages = []
        while not self.message_queue.empty():
            messages.append(await self.message_queue.get())
        return messages

class RateLimiter:
    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.call_times = deque()

    async def wait(self):
        current_time = time.time()
        while self.call_times and current_time - self.call_times[0] >= self.period:
            self.call_times.popleft()
        if len(self.call_times) >= self.max_calls:
            wait_time = self.period - (current_time - self.call_times[0])
            logger.info(f"Rate limit exceeded. Waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        self.call_times.append(current_time)

def retry_on_exception(max_retries=5, initial_delay=1, backoff_factor=2, exceptions=(google.api_core.exceptions.ResourceExhausted,)):
    """Decorator to retry a coroutine upon specific exceptions with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
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
        self.api_key = "AIzaSyACCbhYudSe-lQzqHZp_yi3KSMbka5kTG8"
        if not self.api_key:
            raise ValueError("API key cannot be empty")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.instances: Dict[str, GeminiInstance] = {}
        self.mother_node: Optional[GeminiInstance] = None
        self.rate_limiter = RateLimiter(max_calls=15, period=60)
        self.instance_counter = 0
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, str]:
        try:
            with open('prompts.md', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse sections using markdown headers
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
                
            logger.info(f"Loaded {len(sections)} prompt sections: {list(sections.keys())}")
            return sections
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
            raise ValueError(f"Failed to load prompts: {e}")

    def normalize_instance_id(self, identifier: str) -> str:
        """Normalize instance identifiers to a consistent format."""
        return identifier.replace(" ", "-").lower()

    @retry_on_exception()
    async def _initialize_mother_node(self):
        mother_prompt = self.prompts.get('Mother Node Initialization', '')
        if not mother_prompt:
            raise ValueError("Mother node initialization prompt not found")
            
        chat = self.model.start_chat()
        self.mother_node = GeminiInstance(
            name="mother_node",
            role="scrum_master",
            chat=chat,
            instance_id="mother"
        )
        
        await asyncio.sleep(4.5)
        await self.mother_node.chat.send_message_async(mother_prompt)
        print(f"Scrum Master Node initialized")

    async def create_instance(
        self, 
        role_description: str, 
        initial_prompt: str = "", 
        name: Optional[str] = None, 
        instance_id: Optional[str] = None
    ) -> GeminiInstance:
        if name is None:
            name = f"instance_{len(self.instances)}"
            
        chat = self.model.start_chat()
        await asyncio.sleep(4.5)
        if initial_prompt:
            await chat.send_message_async(initial_prompt)
        
        if instance_id is None:
            self.instance_counter += 1
            instance_id = f"inst_{self.instance_counter}"
        instance_id = self.normalize_instance_id(instance_id)

        instance = GeminiInstance(
            name=name,
            role=role_description,
            chat=chat,
            instance_id=instance_id
        )
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
    async def _get_instance_response(self, instance: GeminiInstance, prompt: str) -> str:
        messages = await instance.receive_messages()
        if messages:
            context = "\n".join([f"Message from {msg['from']}: {msg['content']}" for msg in messages])
            prompt = f"Context from other instances:\n{context}\n\nTask:\n{prompt}"
        
        prompt = self.validate_message(prompt)
        logger.info(f"\nInstance {instance.name} ({instance.role}) received:\n{prompt}\n")
        print(f"{instance.name} ({instance.role}): {prompt}")

        await self.rate_limiter.wait()
        try:
            response = await instance.chat.send_message_async(prompt)
            response_text = response.text
            logger.info(f"Instance {instance.name} responded:\n{response_text}\n")
            print(f"{instance.name} ({instance.role}): {response_text}")
            
            instance.history.append({
                "role": instance.role,
                "text": response_text
            })
            instance.task_completed = True
            return response_text
        except asyncio.TimeoutError:
            logger.error(f"Timeout while waiting for instance {instance.name}")
            return ""
        except Exception as e:
            logger.error(f"Error from instance {instance.name}: {e}")
            raise

    async def synthesize_responses(self, responses: Dict[str, str]) -> str:
        combined = "\n".join(responses.values())
        return combined

    async def connect_instances(self, instance1_id: str, instance2_id: str) -> bool:
        if instance1_id not in self.instances or instance2_id not in self.instances:
            return False
            
        inst1 = self.instances[instance1_id]
        inst2 = self.instances[instance2_id]
        
        inst1.connected_instances[instance2_id] = inst2
        inst2.connected_instances[instance1_id] = inst1
        return True

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
                    if '|' in create_line:
                        role_desc, initial_prompt = [part.strip() for part in create_line.split('|', 1)]
                    else:
                        role_desc = create_line.strip()
                        initial_prompt = ""
                    instance_id = self.normalize_instance_id(role_desc)
                    new_instance = await self.create_instance(
                        role_description=role_desc,
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

        return result

    async def synthesize_with_mother_node(self, node_outputs: List[Tuple[str, str]]) -> str:
        outputs_text = "\n".join([f"{id}: {output}" for id, output in node_outputs])
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
        2. CREATE: Make specialist instances if needed (format: CREATE: role | responsibility)
        3. TO: Assign specific tasks to instances (format: TO instance-id: detailed task)
        4. SYNTHESIZE: At the end

        Current team: {[f"{id}: {inst.role}" for id, inst in self.instances.items()]}

        Rules:
        - Must use ANALYZE, CREATE, TO, and SYNTHESIZE commands
        - Each command must be on its own line
        - Keep responses focused and actionable
        - Always delegate tasks using TO commands
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

async def cli_main():
    api_key = "AIzaSyACCbhYudSe-lQzqHZp_yi3KSMbka5kTG8" #Hardcoded API key as requested
    try:
        async with GeminiNetwork() as network:
            print("Gemini CLI initialized. Type 'exit' or 'quit' to exit.")
            while True:
                try:
                    user_input = input("> ")
                    response = await network.handle_user_input(user_input)
                    print(f"User: {user_input}")
                    print(f"Assistant: {response}")
                except EOFError:
                    print("Connection to Gemini API lost. Please check your internet connection and try again.")
                    break
                except Exception as e:
                    print(f"An error occurred: {e}")
    except Exception as e:
        print(f"A fatal error occurred during initialization: {e}")

if __name__ == "__main__":
    asyncio.run(cli_main())
