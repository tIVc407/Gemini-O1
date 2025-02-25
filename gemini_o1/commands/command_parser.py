"""
Command parsing for Gemini network mother node commands.
"""

import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

class CommandParser:
    """
    Parses and extracts commands from mother node responses.
    """
    
    COMMAND_TYPES = [
        'ANALYZE', 'CREATE', 'TO', 'CONNECT', 'MESSAGE', 'SYNTHESIZE'
    ]
    
    def __init__(self, network):
        """
        Initialize the command parser.
        
        Args:
            network: The GeminiNetwork instance
        """
        self.network = network
        
    def parse_commands(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse a mother node response into a list of command dictionaries.
        
        Args:
            response: The mother node response text
            
        Returns:
            List of command dictionaries with type and parameters
        """
        commands = []
        lines = response.strip().split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            line = line.lstrip('-* ').rstrip()
            
            for cmd_type in self.COMMAND_TYPES:
                if line.startswith(f'{cmd_type}:') or (cmd_type == 'TO' and line.startswith('TO ')):
                    command, next_i = self._extract_command(lines, i, cmd_type)
                    if command:
                        commands.append(command)
                    i = next_i
                    break
            else:
                i += 1
                
        return commands
    
    def _extract_command(self, lines: List[str], start_idx: int, cmd_type: str) -> Tuple[Dict[str, Any], int]:
        """
        Extract a specific command and its parameters.
        
        Args:
            lines: List of response lines
            start_idx: Starting index in the lines list
            cmd_type: Type of command to extract
            
        Returns:
            Tuple of (command_dict, next_index)
        """
        line = lines[start_idx].strip().lstrip('-* ').rstrip()
        i = start_idx + 1
        
        if cmd_type == 'ANALYZE':
            analysis = line[len('ANALYZE:'):].strip()
            return {'type': 'ANALYZE', 'content': analysis}, i
            
        elif cmd_type == 'CREATE':
            create_content = line[len('CREATE:'):].strip()
            create_lines = [create_content] if create_content else []
            
            while i < len(lines):
                next_line = lines[i].strip()
                if not next_line:
                    i += 1
                    continue
                    
                next_line = next_line.lstrip('-* ').rstrip()
                if any(next_line.startswith(c) for c in ['ANALYZE:', 'CREATE:', 'CONNECT:', 'MESSAGE:', 'TO ', 'SYNTHESIZE']):
                    break
                    
                create_lines.append(next_line)
                i += 1
                
            return {'type': 'CREATE', 'lines': create_lines}, i
            
        elif cmd_type == 'TO':
            cmd = line[len('TO '):].strip()
            if ':' in cmd:
                instance_id, prompt = cmd.split(':', 1)
                return {
                    'type': 'TO', 
                    'instance_id': self.network.normalize_instance_id(instance_id.strip()),
                    'prompt': prompt.strip()
                }, i
            else:
                logger.warning(f"Invalid TO command format: {cmd}")
                return None, i
                
        elif cmd_type == 'CONNECT':
            cmd = line[len('CONNECT:'):].strip()
            if '<->' in cmd:
                inst1_id, inst2_id = [id.strip() for id in cmd.split('<->')]
                return {
                    'type': 'CONNECT',
                    'instance1_id': inst1_id,
                    'instance2_id': inst2_id
                }, i
            else:
                logger.warning(f"Invalid CONNECT command format: {cmd}")
                return None, i
                
        elif cmd_type == 'MESSAGE':
            cmd = line[len('MESSAGE:'):].strip()
            if '->' in cmd and ':' in cmd:
                from_to_part, message = cmd.split(':', 1)
                from_id, to_id = [id.strip() for id in from_to_part.split('->')]
                return {
                    'type': 'MESSAGE',
                    'from_id': from_id,
                    'to_id': to_id,
                    'message': message.strip()
                }, i
            else:
                logger.warning(f"Invalid MESSAGE command format: {cmd}")
                return None, i
                
        elif cmd_type == 'SYNTHESIZE':
            return {'type': 'SYNTHESIZE'}, i
            
        return None, i