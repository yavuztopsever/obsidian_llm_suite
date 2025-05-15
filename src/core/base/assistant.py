import os
import logging
from typing import Dict, Any, Optional, List

from src.core.config.manager import ConfigManager
from src.core.prompts.manager import PromptManager
from src.core.llm.client import LLMClient
from src.core.obsidian.formatter import format_obsidian_link, format_obsidian_tag, format_metadata_section, format_note
from src.core.schemas.validator import SchemaValidator
from src.core.logging.setup import get_logger

class BaseAssistant:
    """Base class for all assistant implementations in the Obsidian suite.
    
    This class provides common functionality for all assistants, including:
    - Configuration access
    - Prompt loading
    - LLM client initialization
    - Logging
    - Schema validation
    - Obsidian formatting
    """
    
    def __init__(self, tool_name: str):
        """Initialize the base assistant.
        
        Args:
            tool_name: The name of the tool this assistant belongs to.
                      Used for configuration access and logging.
        """
        self._tool_name = tool_name
        self._config_manager = ConfigManager.get_instance()
        self._prompt_manager = PromptManager(tool_name)
        self._logger = get_logger(f"src.tools.{tool_name}")
        self._schema_validator = SchemaValidator()
        self._obsidian_formatter = {
            "link": format_obsidian_link,
            "tag": format_obsidian_tag,
            "metadata_section": format_metadata_section,
            "note": format_note
        }
        
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a tool-specific configuration value.
        
        Args:
            key: The configuration key (without the tool prefix).
            default: The default value to return if the key is not found.
            
        Returns:
            The configuration value or the default.
        """
        return self._config_manager.get_tool_config(self._tool_name, key, default)
    
    def get_prompt_manager(self) -> PromptManager:
        """Get the prompt manager for this assistant.
        
        Returns:
            The prompt manager instance.
        """
        return self._prompt_manager
    
    def load_system_prompt(self, prompt_name: str, default_prompt: Optional[str] = None) -> str:
        """Load a system prompt by name.
        
        Args:
            prompt_name: The name of the prompt to load.
            default_prompt: The default prompt to use if the named prompt is not found.
            
        Returns:
            The prompt content.
        """
        return self._prompt_manager.get_system_prompt(prompt_name, default_prompt)
    
    def load_user_prompt(self, prompt_name: str, default_prompt: Optional[str] = None) -> str:
        """Load a user prompt by name.
        
        Args:
            prompt_name: The name of the prompt to load.
            default_prompt: The default prompt to use if the named prompt is not found.
            
        Returns:
            The prompt content.
        """
        return self._prompt_manager.get_user_prompt(prompt_name, default_prompt)
    
    def initialize_llm_client(self, client_type: str = "openai") -> LLMClient:
        """Initialize an LLM client.
        
        Args:
            client_type: The type of LLM client to initialize ("openai" or "perplexity").
            
        Returns:
            The initialized LLM client.
        """
        return LLMClient(client_type)
    
    def log_info(self, message: str) -> None:
        """Log an info message.
        
        Args:
            message: The message to log.
        """
        self._logger.info(message)
    
    def log_error(self, message: str) -> None:
        """Log an error message.
        
        Args:
            message: The message to log.
        """
        self._logger.error(message)
    
    def log_warning(self, message: str) -> None:
        """Log a warning message.
        
        Args:
            message: The message to log.
        """
        self._logger.warning(message)
    
    def log_debug(self, message: str) -> None:
        """Log a debug message.
        
        Args:
            message: The message to log.
        """
        self._logger.debug(message)