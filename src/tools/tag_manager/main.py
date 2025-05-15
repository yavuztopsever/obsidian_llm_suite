import argparse
import os
import sys
from typing import Set, Dict, Optional
import shutil

# Core library imports
from src.core.config.loader import get_config
from src.core.file_io.utils import scan_directory, read_file, write_file
from src.core.logging.setup import get_logger
from src.core.di.setup import setup_container

# Local tool import
from .assistant import TagManagerAssistant

# Get a logger for this module
logger = get_logger(__name__)

def backup_file(file_path: str) -> Optional[str]:
    """Creates a backup copy of the file with a .bak extension."""
    backup_path = file_path + ".bak"
    try:
        shutil.copy2(file_path, backup_path) # copy2 preserves metadata
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup for {file_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Scan an Obsidian vault, standardize tags using an LLM, and update notes.")
    parser.add_argument("--dry-run", action="store_true", help="Scan and show proposed changes without modifying files.")
    # Add other arguments like --vault-path if needed to override config
    args = parser.parse_args()

    logger.info(f"Starting Tag Manager run... (Dry Run: {args.dry_run})")

    try:
        # --- Configuration and Initialization ---
        vault_path = get_config('obsidian_vault_path')
        if not vault_path or not os.path.isdir(vault_path):
            logger.error(f"Obsidian vault path not found or invalid in configuration: '{vault_path}'")
            logger.error("Please ensure 'obsidian_vault_path' is correctly set in config/settings.yaml")
            sys.exit(1)
        logger.info(f"Using Obsidian vault path: {vault_path}")

        try:
            # Initialize the dependency injection container
            setup_container()
            
            # Create the TagManagerAssistant
            assistant = TagManagerAssistant()
        except ValueError as e:
            logger.error(f"Initialization failed: {e}")
            sys.exit(1)

        # --- Phase 1: Scan Vault and Collect All Tags ---
        logger.info(f"Scanning vault for markdown files: {vault_path}")
        all_note_files = scan_directory(vault_path, extension='.md')
        if not all_note_files:
            logger.info("No markdown files found in the vault. Exiting.")
            sys.exit(0)
        logger.info(f"Found {len(all_note_files)} markdown files.")

        all_vault_tags: Set[str] = set()
        files_with_errors = []
        logger.info("Collecting all unique tags from vault...")
        for note_file in all_note_files:
            try:
                content = read_file(note_file)
                tags_in_file = assistant.find_tags_in_content(content)
                all_vault_tags.update(tags_in_file)
            except FileNotFoundError:
                logger.error(f"File not found during tag collection: {note_file}")
                files_with_errors.append(note_file)
            except IOError as e:
                logger.error(f"I/O error reading file {note_file} for tags: {e}")
                files_with_errors.append(note_file)
            except Exception as e:
                logger.exception(f"Unexpected error collecting tags from {note_file}: {e}")
                files_with_errors.append(note_file)

        if not all_vault_tags:
            logger.info("No tags found in any files. Exiting.")
            sys.exit(0)

        logger.info(f"Collected {len(all_vault_tags)} unique tags across the vault.")
        # logger.debug(f"All unique tags found: {sorted(list(all_vault_tags))}") # Optional: Log all tags

        # --- Phase 2: Get Standardization Map from LLM ---
        logger.info("Requesting tag standardization map from LLM...")
        standardization_map = assistant.get_standardization_map(all_vault_tags)

        if standardization_map is None:
            logger.error("Failed to obtain tag standardization map from LLM. Aborting update phase.")
            sys.exit(1)

        if not standardization_map:
            logger.info("No tags required standardization according to the LLM. Exiting.")
            sys.exit(0)

        # Filter map to only include actual changes
        changes_map = {k: v for k, v in standardization_map.items() if k != v and k not in assistant.exempt_tags}
        if not changes_map:
             logger.info("LLM map received, but no actual changes needed after filtering exempt tags and self-mappings. Exiting.")
             sys.exit(0)

        logger.info(f"LLM proposed {len(changes_map)} tag standardizations:")
        for old, new in changes_map.items():
            logger.info(f"  '{old}' -> '{new}'")

        # --- Phase 3: Apply Standardization to Files ---
        logger.info("Applying standardization map to vault files...")
        files_updated = 0
        files_failed_update = 0
        files_skipped_backup = 0

        # Iterate through files again (excluding those that failed reading earlier)
        files_to_process = [f for f in all_note_files if f not in files_with_errors]

        for note_file in files_to_process:
            try:
                original_content = read_file(note_file)
                modified_content = assistant.standardize_tags_in_content(original_content, changes_map)

                if modified_content:
                    if args.dry_run:
                        logger.info(f"[Dry Run] Changes proposed for: {note_file}")
                        # Optionally log diff or specific changes here
                        files_updated += 1
                    else:
                        if backup_file(note_file):
                            write_file(note_file, modified_content)
                            logger.info(f"Successfully updated tags in: {note_file}")
                            files_updated += 1
                        else:
                            logger.warning(f"Skipping write for {note_file} due to backup failure.")
                            files_skipped_backup += 1

            except FileNotFoundError:
                logger.error(f"File not found during update phase: {note_file}")
                files_failed_update += 1
            except IOError as e:
                logger.error(f"I/O error writing file {note_file}: {e}")
                files_failed_update += 1
            except Exception as e:
                logger.exception(f"Unexpected error updating tags in {note_file}: {e}")
                files_failed_update += 1

        logger.info("--- Tag Standardization complete ---")
        logger.info(f"Files scanned: {len(all_note_files)}")
        logger.info(f"Files with read errors: {len(files_with_errors)}")
        logger.info(f"Files updated (or proposed in dry run): {files_updated}")
        logger.info(f"Files failed during update: {files_failed_update}")
        logger.info(f"Files skipped due to backup failure: {files_skipped_backup}")
        if args.dry_run:
            logger.warning("Dry run complete. No files were modified.")

    except Exception as e:
        logger.exception(f"A critical error occurred during script execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
