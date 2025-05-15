import argparse
import os
import sys
import shutil  # Added for file copying
from typing import Optional  # Added Optional type hint

# Add the project root directory to the Python module search path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.insert(0, project_root)

# Core library imports
from src.core.config.loader import get_config
from src.core.file_io.utils import scan_directory, read_file, write_file
from src.core.logging.setup import get_logger
from src.core.di.setup import setup_container

# Local tool import
from src.tools.template_manager.assistant import TemplateManagerAssistant

# Get a logger for this module
logger = get_logger(__name__)

def backup_file(file_path: str) -> Optional[str]:
    """Creates a backup copy of the file with a .bak extension."""
    backup_path = file_path + ".bak"
    try:
        shutil.copy2(file_path, backup_path)  # copy2 preserves metadata
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup for {file_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Process markdown notes to apply a standard template using an LLM.")
    parser.add_argument("--file", type=str, help="Path to a single markdown file to process.")
    # Add other arguments as needed, e.g., --vault-path to override config
    args = parser.parse_args()

    try:
        # Get vault path from config - crucial for scanning
        vault_path = get_config('obsidian_vault_path')
        if not vault_path or not os.path.isdir(vault_path):
            logger.error(f"Obsidian vault path not found or invalid in configuration: '{vault_path}'")
            logger.error("Please ensure 'obsidian_vault_path' is correctly set in config/settings.yaml")
            sys.exit(1)
        logger.info(f"Using Obsidian vault path: {vault_path}")

        # Initialize the dependency injection container and assistant
        try:
            # Initialize the dependency injection container
            setup_container()
            
            # Create the TemplateManagerAssistant
            assistant = TemplateManagerAssistant()
        except ValueError as e:
            logger.error(f"Initialization failed: {e}")
            sys.exit(1)

        note_files_to_process = []
        if args.file:
            # Process a single file
            file_path = os.path.abspath(args.file)
            if not os.path.isfile(file_path):
                logger.error(f"Specified file not found: {file_path}")
                sys.exit(1)
            if not file_path.endswith('.md'):
                logger.error(f"Specified file is not a markdown file: {file_path}")
                sys.exit(1)
            note_files_to_process.append(file_path)
            logger.info(f"Processing single file: {file_path}")
        else:
            # Scan the vault directory
            logger.info(f"Scanning vault for markdown files: {vault_path}")
            note_files_to_process = scan_directory(vault_path, extension='.md')
            if not note_files_to_process:
                logger.info("No markdown files found in the vault.")
                sys.exit(0)
            logger.info(f"Found {len(note_files_to_process)} markdown files to process.")

        # Process each file
        processed_count = 0
        failed_count = 0
        skipped_count = 0  # Keep track of skipped backups
        for note_file in note_files_to_process:
            logger.info(f"--- Processing file: {note_file} ---")
            try:
                original_content = read_file(note_file)
                # Log start of original content for this file
                logger.debug(f"Read original content for {os.path.basename(note_file)} (start): {original_content[:150]}...")

                processed_content = assistant.process_note_content(original_content)

                if processed_content:
                    # Log start of processed content before writing
                    logger.debug(f"Processed content to write for {os.path.basename(note_file)} (start): {processed_content[:150]}...")
                    # Create backup before writing
                    if backup_file(note_file):
                        write_file(note_file, processed_content)
                        logger.info(f"Successfully processed and saved: {note_file}")
                        processed_count += 1
                    else:
                        logger.warning(f"Skipping write for {note_file} due to backup failure.")
                        skipped_count += 1
                else:
                    logger.error(f"Failed to process content for: {note_file}")
                    failed_count += 1

            except FileNotFoundError:
                logger.error(f"File not found during processing loop (should not happen if scan worked): {note_file}")
                failed_count += 1
            except IOError as e:
                logger.error(f"I/O error processing file {note_file}: {e}")
                failed_count += 1
            except Exception as e:
                logger.exception(f"An unexpected error occurred processing file {note_file}: {e}")
                failed_count += 1

        logger.info("--- Processing complete ---")
        logger.info(f"Successfully processed: {processed_count}")
        logger.info(f"Failed to process: {failed_count}")
        logger.info(f"Skipped due to backup failure: {skipped_count}")

    except Exception as e:
        logger.exception(f"A critical error occurred during script execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
