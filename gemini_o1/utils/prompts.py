"""
Prompt loading and management utilities.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class PromptManager:
    """
    Manages loading and retrieving prompts from markdown files.
    """
    
    def __init__(self, prompt_file: str = 'prompts.md'):
        """
        Initialize the prompt manager.
        
        Args:
            prompt_file: Path to the markdown file containing prompts
        """
        self.prompt_file = prompt_file
        self.prompts = self._load_prompts()
        
    def _load_prompts(self) -> Dict[str, str]:
        """
        Load prompts from the markdown file.
        
        Returns:
            Dictionary mapping section names to prompt content
        
        Raises:
            ValueError: If no prompts could be loaded
        """
        try:
            with open(self.prompt_file, 'r', encoding='utf-8') as f:
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
    
    def get_prompt(self, section_name: str, default: str = "") -> str:
        """
        Get a prompt by section name.
        
        Args:
            section_name: The name of the prompt section
            default: Default value to return if section not found
            
        Returns:
            The prompt text or default value
        """
        return self.prompts.get(section_name, default)
    
    def format_prompt(self, section_name: str, **kwargs) -> str:
        """
        Get and format a prompt with the provided variables.
        
        Args:
            section_name: The name of the prompt section
            **kwargs: Variables to format into the prompt
            
        Returns:
            The formatted prompt text
        """
        prompt = self.get_prompt(section_name)
        if prompt:
            return prompt.format(**kwargs)
        return ""
        
    def reload(self) -> None:
        """Reload prompts from file."""
        self.prompts = self._load_prompts()