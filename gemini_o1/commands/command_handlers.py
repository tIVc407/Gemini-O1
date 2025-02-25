"""
Handlers for processing different command types.
"""

import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

class CommandHandler:
    """
    Base class for command handlers.
    """
    
    def __init__(self, network):
        """
        Initialize the command handler.
        
        Args:
            network: The GeminiNetwork instance
        """
        self.network = network
    
    async def handle_commands(self, commands: List[Dict[str, Any]]) -> Dict:
        """
        Process a list of parsed commands.
        
        Args:
            commands: List of command dictionaries
            
        Returns:
            Result dictionary with actions taken, responses, and new instances
        """
        result = {
            "actions_taken": [],
            "responses": {},
            "new_instances": []
        }
        
        # Reset task completion status for all instances
        for instance in self.network.instances.values():
            instance.task_completed = False
        
        # Track outputs from nodes for context in later commands
        node_outputs = []
        
        # Process each command in sequence
        for command in commands:
            cmd_type = command.get('type')
            if cmd_type == 'ANALYZE':
                self._handle_analyze(command, result)
            elif cmd_type == 'CREATE':
                await self._handle_create(command, result)
            elif cmd_type == 'TO':
                await self._handle_to(command, result, node_outputs)
            elif cmd_type == 'CONNECT':
                await self._handle_connect(command, result)
            elif cmd_type == 'MESSAGE':
                await self._handle_message(command, result)
            elif cmd_type == 'SYNTHESIZE':
                await self._handle_synthesize(result, node_outputs)
                
        # Connect all instances to each other for full mesh communication
        for inst_id in self.network.instances:
            for other_id in self.network.instances:
                if inst_id != other_id:
                    await self.network.connect_instances(inst_id, other_id)
                    
        return result
        
    def _handle_analyze(self, command: Dict[str, Any], result: Dict) -> None:
        """Handle ANALYZE command."""
        analysis = command.get('content', '')
        result["actions_taken"].append(f"Analyzed task: {analysis}")
        
    async def _handle_create(self, command: Dict[str, Any], result: Dict) -> None:
        """Handle CREATE command."""
        create_lines = command.get('lines', [])
        
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
                
            instance_id = self.network.normalize_instance_id(role_desc)
            
            new_instance = await self.network.create_instance(
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
            
    async def _handle_to(self, command: Dict[str, Any], result: Dict, node_outputs: List[Tuple[str, str]]) -> None:
        """Handle TO command."""
        instance_id = command.get('instance_id')
        prompt = command.get('prompt')
        
        if not instance_id or not prompt:
            logger.warning(f"Missing instance_id or prompt in TO command")
            return
            
        # Add context from previous outputs if available
        previous_outputs_text = "\n".join(
            [f"{id}: {output}" for id, output in node_outputs]
        )
        
        if previous_outputs_text:
            instance_prompt = f"Previous outputs:\n{previous_outputs_text}\n\nTask:\n{prompt}"
        else:
            instance_prompt = prompt
            
        if instance_id in self.network.instances:
            instance_response = await self.network.get_instance_response(
                self.network.instances[instance_id],
                instance_prompt
            )
            
            if instance_response:
                result["responses"][instance_id] = instance_response
                node_outputs.append((instance_id, instance_response))
                result["actions_taken"].append(f"Got response from instance {instance_id}")
        else:
            logger.warning(f"Instance {instance_id} not found for TO command.")
            
    async def _handle_connect(self, command: Dict[str, Any], result: Dict) -> None:
        """Handle CONNECT command."""
        inst1_id = command.get('instance1_id')
        inst2_id = command.get('instance2_id')
        
        if not inst1_id or not inst2_id:
            logger.warning("Missing instance IDs in CONNECT command")
            return
            
        if await self.network.connect_instances(inst1_id, inst2_id):
            action_message = f"Connected instances {inst1_id} <-> {inst2_id}"
            result["actions_taken"].append(action_message)
            logger.info(action_message)
        else:
            logger.warning(f"Failed to connect instances {inst1_id} and {inst2_id}")
            
    async def _handle_message(self, command: Dict[str, Any], result: Dict) -> None:
        """Handle MESSAGE command."""
        from_id = command.get('from_id')
        to_id = command.get('to_id')
        message = command.get('message')
        
        if not from_id or not to_id or not message:
            logger.warning("Missing parameters in MESSAGE command")
            return
            
        if from_id in self.network.instances and to_id in self.network.instances:
            await self.network.instances[from_id].send_message_to(to_id, message)
            result["actions_taken"].append(f"Sent message from {from_id} to {to_id}")
        else:
            logger.warning(f"Invalid MESSAGE command: {from_id} -> {to_id}")
            
    async def _handle_synthesize(self, result: Dict, node_outputs: List[Tuple[str, str]]) -> None:
        """Handle SYNTHESIZE command."""
        synthesized_response = await self.network.synthesize_with_mother_node(node_outputs)
        
        if synthesized_response:
            result["responses"]["synthesized"] = synthesized_response
            result["actions_taken"].append("Synthesized responses from all instances")
        else:
            logger.warning("Failed to synthesize responses with mother node.")