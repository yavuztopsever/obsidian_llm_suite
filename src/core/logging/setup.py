import logging
import sys
from logging.handlers import RotatingFileHandler
import os

# Import config loader to potentially get log settings
from src.core.config.loader import get_config # Fixed import

# --- Configuration ---
LOG_LEVEL_STR = get_config('logging.level', 'INFO').upper() # Default to INFO
LOG_FORMAT = get_config('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_DATE_FORMAT = get_config('logging.date_format', '%Y-%m-%d %H:%M:%S')

# File logging configuration (optional, based on config)
ENABLE_FILE_LOGGING = get_config('logging.file.enable', False)
LOG_FILE_PATH = get_config('logging.file.path', 'obsidian_suite.log') # Relative to project root or absolute
LOG_FILE_MAX_BYTES = int(get_config('logging.file.max_bytes', 1024 * 1024 * 5)) # Default 5MB
LOG_FILE_BACKUP_COUNT = int(get_config('logging.file.backup_count', 3))

# --- Setup ---
_loggers = {}

def setup_logging():
    """Configures the root logger and potentially file/stream handlers."""
    log_level = getattr(logging, LOG_LEVEL_STR, logging.INFO)

    # Get the root logger
    root_logger = logging.getLogger()
    # Check if handlers are already configured to avoid duplication
    if root_logger.hasHandlers():
        # Optionally clear existing handlers if re-configuration is desired
        # for handler in root_logger.handlers[:]:
        #     root_logger.removeHandler(handler)
        return # Already configured

    root_logger.setLevel(log_level)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Console Handler (always add)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File Handler (optional)
    if ENABLE_FILE_LOGGING:
        try:
            # Ensure log directory exists if path includes directories
            log_dir = os.path.dirname(LOG_FILE_PATH)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            file_handler = RotatingFileHandler(
                LOG_FILE_PATH,
                maxBytes=LOG_FILE_MAX_BYTES,
                backupCount=LOG_FILE_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            root_logger.info(f"File logging enabled: {LOG_FILE_PATH}")
        except Exception as e:
            root_logger.error(f"Failed to set up file logging at {LOG_FILE_PATH}: {e}", exc_info=True)

    root_logger.info(f"Logging configured. Level: {LOG_LEVEL_STR}")

def get_logger(name: str) -> logging.Logger:
    """Gets a logger instance configured with the project's settings.

    Args:
        name: The name for the logger (usually __name__ of the calling module).

    Returns:
        A configured logging.Logger instance.
    """
    # Ensure root logger is configured first
    # This might run multiple times but setup_logging prevents duplication
    setup_logging()

    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    # Logger level will be inherited from root unless set explicitly
    # logger.setLevel(log_level) # Usually not needed if root is set

    # Add handlers directly to this logger only if specific behavior is needed,
    # otherwise, let messages propagate to the root logger's handlers.

    _loggers[name] = logger
    return logger

# --- Initial configuration call ---
# Configure logging when this module is imported
setup_logging()

# Example Usage (can be removed or moved to tests)
if __name__ == '__main__':
    # Example of getting loggers in different modules
    logger_main = get_logger(__name__)
    logger_tool = get_logger('obsidian_suite.tools.some_tool')

    logger_main.debug("This is a debug message.") # Won't show if level is INFO
    logger_main.info("This is an info message.")
    logger_tool.warning("This is a warning from the tool.")
    logger_main.error("This is an error message.")
    try:
        1 / 0
    except ZeroDivisionError:
        logger_main.exception("An exception occurred!")
