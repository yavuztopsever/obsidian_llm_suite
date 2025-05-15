import os
import yaml
from dotenv import load_dotenv
from typing import Any, Optional

# Determine the absolute path to the config directory relative to this file
# This assumes loader.py is in src/core/config/
CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config'))
SETTINGS_FILE = os.path.join(CONFIG_DIR, 'settings.yaml')
ENV_FILE = os.path.join(CONFIG_DIR, '.env')

_config = None

def load_config() -> dict:
    """Loads configuration from settings.yaml and .env file."""
    global _config
    if _config is not None:
        return _config

    config_data = {}

    # Load from settings.yaml
    try:
        with open(SETTINGS_FILE, 'r') as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                config_data.update(yaml_config)
    except FileNotFoundError:
        # It's okay if settings.yaml doesn't exist, maybe only .env is used
        pass
    except yaml.YAMLError as e:
        # Log this error appropriately in a real application
        print(f"Error parsing YAML file {SETTINGS_FILE}: {e}")

    # Load from .env file (overrides yaml settings if keys conflict)
    # load_dotenv will search for .env in the current working directory
    # or parent directories, or you can specify the path.
    # Loading it from the specific config dir ensures consistency.
    if os.path.exists(ENV_FILE):
        load_dotenv(dotenv_path=ENV_FILE, override=True)
    else:
        # Also try loading .env from the project root (one level above config dir)
        project_root_env = os.path.join(CONFIG_DIR, '..', '.env')
        if os.path.exists(project_root_env):
            load_dotenv(dotenv_path=project_root_env, override=True)

    # Add environment variables to config_data
    # Prioritize environment variables over YAML file settings
    # Example: Get specific keys expected from .env
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        config_data['openai_api_key'] = openai_key

    perplexity_key = os.getenv('PERPLEXITY_API_KEY')
    if perplexity_key:
        config_data['perplexity_api_key'] = perplexity_key

    # You might want to load other specific env vars or iterate os.environ
    # Be careful about sensitive data if iterating os.environ

    _config = config_data
    return _config

def get_config(key: str, default: Optional[Any] = None) -> Any:
    """Retrieves a configuration value by key.

    Args:
        key: The configuration key (can use dot notation for nested keys, e.g., 'tag_manager.exempt_tags').
        default: The default value to return if the key is not found.

    Returns:
        The configuration value or the default.
    """
    config = load_config()
    keys = key.split('.')
    value = config
    try:
        for k in keys:
            if isinstance(value, dict):
                value = value[k]
            else:
                # Handle case where intermediate key is not a dict
                return default
        return value
    except KeyError:
        return default

# Initialize config on module load
load_config()
