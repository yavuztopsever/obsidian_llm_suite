import os
from typing import Dict, Any, Optional

from src.core.config.loader import load_config, get_config as get_config_from_loader

class ConfigManager:
    """Singleton manager for configuration access."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize the config manager."""
        self._config_cache = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from files and environment."""
        self._config_cache = load_config()
    
    def reload(self):
        """Reload configuration."""
        self._load_config()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: The configuration key (can use dot notation for nested keys).
            default: The default value to return if the key is not found.
            
        Returns:
            The configuration value or the default.
        """
        return get_config_from_loader(key, default)
    
    def get_tool_config(self, tool_name: str, key: str, default: Any = None) -> Any:
        """Get a tool-specific configuration value.
        
        Args:
            tool_name: The name of the tool.
            key: The configuration key (without the tool prefix).
            default: The default value to return if the key is not found.
            
        Returns:
            The configuration value or the default.
        """
        full_key = f"{tool_name}.{key}"
        return self.get(full_key, default)
    
    def get_core_config(self, component: str, key: str, default: Any = None) -> Any:
        """Get a core component configuration value.
        
        Args:
            component: The name of the core component.
            key: The configuration key (without the component prefix).
            default: The default value to return if the key is not found.
            
        Returns:
            The configuration value or the default.
        """
        full_key = f"core.{component}.{key}"
        return self.get(full_key, default)