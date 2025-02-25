"""
Response handling and generation logic.
"""

import logging
from typing import Dict, List, Optional, Tuple

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from ..utils.retry import retry_on_exception
from ..models.instance import GeminiInstance

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """
    Handles generating responses from Gemini instances.
    """
    
    def __init__(self, network):
        """
        Initialize the response generator.
        
        Args:
            network: The GeminiNetwork instance
        """
        self.network = network
        
    def validate_message(self, message: str) -> str:
        """
        Validate a message before sending to the API.
        
        Args:
            message: The message to validate
            
        Returns:
            The validated message
            
        Raises:
            ValueError: If the message is invalid
        """
        if not message or not isinstance(message, str):
            raise ValueError("Invalid message format")
        return message.strip()
    
    def _build_context(self, instance: GeminiInstance, prompt: str) -> str:
        """
        Build context for the instance response.
        
        Args:
            instance: The GeminiInstance
            prompt: The original prompt
            
        Returns:
            The prompt with added context
        """
        final_prompt = prompt
        
        # Add message context if available
        messages = []
        try:
            # Messages will be retrieved asynchronously later
            # This is just preparation for the async call
            pass
        except Exception as e:
            logger.error(f"Error getting messages for instance {instance.name}: {e}")
            
        # Add previous outputs context if available
        if instance.outputs:
            previous_outputs_text = "\n".join(instance.outputs)
            final_prompt = f"Previous outputs:\n{previous_outputs_text}\n\nTask:\n{final_prompt}"
            
        # Add context from other instances if available
        other_outputs = []
        for inst_id, inst in self.network.instances.items():
            if inst_id != instance.instance_id and inst.outputs:
                other_outputs.append(f"{inst_id}: {inst.outputs[-1]}")
        
        if other_outputs:
            other_outputs_text = "\n".join(other_outputs)
            final_prompt = f"Outputs from other instances:\n{other_outputs_text}\n\nTask:\n{final_prompt}"
            
        return final_prompt
        
    @retry_on_exception()
    async def get_instance_response(
        self, 
        instance: GeminiInstance, 
        prompt: str,
        is_system: bool = False
    ) -> str:
        """
        Get a response from an instance.
        
        Args:
            instance: The GeminiInstance
            prompt: The prompt to send
            is_system: Whether this is a system prompt
            
        Returns:
            The response text
            
        Raises:
            Exception: If there is an error generating the response
        """
        # Add context from messages received by this instance
        messages = await instance.receive_messages()
        if messages:
            context = "\n".join([f"Message from {msg['from']}: {msg['content']}" for msg in messages])
            prompt = f"Context from other instances:\n{context}\n\nTask:\n{prompt}"
            
        # Add context from current state
        prompt = self._build_context(instance, prompt)
        
        # Validate the final prompt
        prompt = self.validate_message(prompt)
        logger.info(f"\nInstance {instance.name} ({instance.role}) received:\n{prompt}\n")
        print(f"{instance.name} ({instance.role}): {prompt}")
        
        # Wait for rate limiting
        await self.network.rate_limiter.async_wait()
        response_text = ""
        
        try:
            model = genai.GenerativeModel(instance.model_name)
            
            # Set system prompt based on role
            system_prompt = self._get_system_prompt_for_role(instance.role)
            
            try:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}" if system_prompt else prompt
                response = model.generate_content(full_prompt)
                response_text = response.text
                
                logger.info(f"Instance {instance.name} responded:\n{response_text}\n")
                print(f"{instance.name} ({instance.role}): {response_text}")
                
                if not is_system:
                    instance.add_to_history(response_text)
                    
            except ResourceExhausted as e:
                logger.error(f"Resource exhausted error: {e}")
                raise
            except Exception as e:
                logger.error(f"Error generating content: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Error from instance {instance.name}: {e}")
            raise
            
        return response_text
        
    def _get_system_prompt_for_role(self, role: str) -> Optional[str]:
        """
        Get the appropriate system prompt for a role.
        
        Args:
            role: The instance role
            
        Returns:
            The system prompt or None
        """
        if role == "scrum_master":
            return self.network.prompt_manager.get_prompt('Mother Node Initialization')
        elif role == "assistant":
            return self.network.prompt_manager.get_prompt('Direct Command Template')
        else:
            # For specialized instances
            return self.network.prompt_manager.get_prompt('Synthesis Prompt')
            
    async def synthesize_responses(self, responses: Dict[str, str]) -> str:
        """
        Combine responses from multiple instances.
        
        Args:
            responses: Dictionary mapping instance IDs to response texts
            
        Returns:
            The combined response text
        """
        combined = "\n".join(responses.values())
        return combined