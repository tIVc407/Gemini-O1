"""
GeminiInstance class for representing individual AI agents.
"""

import time
import uuid
from asyncio import Queue
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


@dataclass
class GeminiInstance:
    """
    Represents an individual AI instance within the Gemini network.
    
    Each instance has its own role, history, and can communicate with other instances.
    """
    name: str
    role: str
    model_name: str
    network: 'GeminiNetwork'  # Forward reference
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    history: List[Dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    message_queue: Queue = field(default_factory=Queue)
    connected_instances: Dict[str, 'GeminiInstance'] = field(default_factory=dict)
    task_completed: bool = field(default=False)
    outputs: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize instance after creation."""
        if not self.history:
            self.history = []
            
    async def send_message_to(self, target_id: str, message: str) -> None:
        """
        Send a message to another instance.
        
        Args:
            target_id: The ID of the target instance
            message: The message content
        """
        if target_id in self.network.instances:
            await self.network.instances[target_id].message_queue.put({
                'from': self.instance_id,
                'content': message
            })
            
    async def receive_messages(self) -> List[Dict[str, str]]:
        """
        Receive all messages in the queue.
        
        Returns:
            A list of message dictionaries
        """
        messages = []
        while not self.message_queue.empty():
            messages.append(await self.message_queue.get())
        return messages

    def add_to_history(self, text: str, is_system: bool = False) -> None:
        """
        Add a message to the instance's history.
        
        Args:
            text: The message text
            is_system: Whether this is a system message
        """
        if not is_system:
            self.history.append({
                "role": self.role,
                "text": text
            })
            self.outputs.append(text)
            self.task_completed = True

    def get_status(self) -> Dict:
        """
        Get the current status of this instance.
        
        Returns:
            A dictionary with instance status information
        """
        return {
            "id": self.instance_id,
            "name": self.name,
            "role": self.role,
            "model": self.model_name,
            "created_at": self.created_at,
            "task_completed": self.task_completed,
            "message_count": len(self.history),
            "connected_to": list(self.connected_instances.keys())
        }