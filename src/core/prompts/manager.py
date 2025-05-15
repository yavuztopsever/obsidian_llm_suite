import os
from typing import Dict, Any, Optional

from src.core.config.loader import get_config
from src.core.file_io.utils import read_file
from src.core.logging.setup import get_logger

logger = get_logger(__name__)

class PromptManager:
    """Manages loading and caching of prompts."""
    
    def __init__(self, config_prefix: str):
        """Initialize the prompt manager.
        
        Args:
            config_prefix: The configuration prefix for this prompt manager.
                          Used to locate prompt files in the configuration.
        """
        self.config_prefix = config_prefix
        self.cache = {}
        
    def get_system_prompt(self, prompt_name: str, default_prompt: Optional[str] = None) -> str:
        """Gets a system prompt by name, from config or default.
        
        Args:
            prompt_name: The name of the prompt to load.
            default_prompt: The default prompt to use if the named prompt is not found.
            
        Returns:
            The prompt content.
            
        Raises:
            ValueError: If no prompt is found and no default is provided.
        """
        cache_key = f"system_{prompt_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        # Try to load from config
        config_key = f"{self.config_prefix}.system_prompts.{prompt_name}"
        prompt_path = get_config(config_key)
        
        if prompt_path and os.path.exists(prompt_path):
            try:
                prompt = read_file(prompt_path)
                self.cache[cache_key] = prompt
                logger.info(f"Loaded system prompt '{prompt_name}' from {prompt_path}")
                return prompt
            except Exception as e:
                logger.error(f"Error loading prompt from {prompt_path}: {e}")
                
        # Use default if provided
        if default_prompt:
            self.cache[cache_key] = default_prompt
            logger.info(f"Using default system prompt for '{prompt_name}'")
            return default_prompt
            
        raise ValueError(f"No prompt found for {prompt_name}")
        
    def get_user_prompt(self, prompt_name: str, default_prompt: Optional[str] = None) -> str:
        """Gets a user prompt by name, from config or default.
        
        Args:
            prompt_name: The name of the prompt to load.
            default_prompt: The default prompt to use if the named prompt is not found.
            
        Returns:
            The prompt content.
            
        Raises:
            ValueError: If no prompt is found and no default is provided.
        """
        cache_key = f"user_{prompt_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        # Try to load from config
        config_key = f"{self.config_prefix}.user_prompts.{prompt_name}"
        prompt_path = get_config(config_key)
        
        if prompt_path and os.path.exists(prompt_path):
            try:
                prompt = read_file(prompt_path)
                self.cache[cache_key] = prompt
                logger.info(f"Loaded user prompt '{prompt_name}' from {prompt_path}")
                return prompt
            except Exception as e:
                logger.error(f"Error loading prompt from {prompt_path}: {e}")
                
        # Use default if provided
        if default_prompt:
            self.cache[cache_key] = default_prompt
            logger.info(f"Using default user prompt for '{prompt_name}'")
            return default_prompt
            
        raise ValueError(f"No prompt found for {prompt_name}")