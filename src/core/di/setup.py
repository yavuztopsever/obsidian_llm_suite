from src.core.di.container import ServiceContainer
from src.core.config.manager import ConfigManager
from src.core.obsidian.formatter import format_obsidian_link, format_obsidian_tag, format_metadata_section, format_note
from src.core.schemas.validator import SchemaValidator
from src.core.logging.setup import get_logger

logger = get_logger(__name__)

def register_core_services():
    """Register core services in the container."""
    logger.info("Registering core services...")
    
    # Register config manager
    config_manager = ConfigManager.get_instance()
    ServiceContainer.register("config_manager", config_manager)
    
    # Register schema validator
    schema_validator = SchemaValidator()
    ServiceContainer.register("schema_validator", schema_validator)
    
    logger.info("Core services registered successfully.")

def register_tool_services():
    """Register tool services in the container.
    
    This function should be called after all tool assistants have been imported.
    """
    logger.info("Registering tool services...")
    
    # Import tool assistants here to avoid circular imports
    try:
        from src.tools.tag_manager.assistant import TagManagerAssistant
        tag_manager = TagManagerAssistant()
        ServiceContainer.register("tag_manager", tag_manager)
        logger.info("Registered TagManagerAssistant")
    except ImportError as e:
        logger.warning(f"Could not import TagManagerAssistant: {e}")
    except Exception as e:
        logger.error(f"Error registering TagManagerAssistant: {e}")
    
    try:
        from src.tools.template_manager.assistant import TemplateManagerAssistant
        template_manager = TemplateManagerAssistant()
        ServiceContainer.register("template_manager", template_manager)
        logger.info("Registered TemplateManagerAssistant")
    except ImportError as e:
        logger.warning(f"Could not import TemplateManagerAssistant: {e}")
    except Exception as e:
        logger.error(f"Error registering TemplateManagerAssistant: {e}")
        
    try:
        from src.tools.enricher.assistant import EnricherAssistant
        enricher = EnricherAssistant()
        ServiceContainer.register("enricher", enricher)
        logger.info("Registered EnricherAssistant")
    except ImportError as e:
        logger.warning(f"Could not import EnricherAssistant: {e}")
    except Exception as e:
        logger.error(f"Error registering EnricherAssistant: {e}")
        
    try:
        from src.tools.researcher.assistant import ResearchAssistant
        researcher = ResearchAssistant()
        ServiceContainer.register("researcher", researcher)
        logger.info("Registered ResearchAssistant")
    except ImportError as e:
        logger.warning(f"Could not import ResearchAssistant: {e}")
    except Exception as e:
        logger.error(f"Error registering ResearchAssistant: {e}")
    
    # Additional tool registrations will be added here as they are refactored
    
    logger.info("Tool services registration complete.")

def setup_container():
    """Set up the service container with all required services and return it."""
    logger.info("Setting up service container...")
    register_core_services()
    register_tool_services()
    logger.info("Service container setup complete.")
    # Return the ServiceContainer class itself, assuming .get is a class method
    return ServiceContainer