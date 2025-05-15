#!/usr/bin/env python3
# filepath: /home/yavuz/Projects/obsidian_suite/apply_enrichment.py
"""
A simple script to apply advanced enrichment to an Obsidian note.
Usage: python apply_enrichment.py /path/to/note.md
"""

import sys
import os
from src.core.di.setup import setup_container
from src.tools.enricher.assistant import EnricherAssistant
from src.core.logging.setup import get_logger

logger = get_logger(__name__)

def main():
    """Apply advanced enrichment to the specified Obsidian note."""
    if len(sys.argv) != 2:
        print("Usage: python apply_enrichment.py /path/to/note.md")
        sys.exit(1)
    
    input_filepath = os.path.abspath(sys.argv[1])
    
    if not os.path.exists(input_filepath):
        logger.error(f"Input file not found: {input_filepath}")
        sys.exit(1)
    
    try:
        print(f"Initializing dependency injection container...")
        # Initialize the dependency injection container
        setup_container()
        
        print(f"Creating EnricherAssistant...")
        # Create the EnricherAssistant
        assistant = EnricherAssistant()
        
        print(f"Starting advanced enrichment based on: {input_filepath}")
        logger.info(f"Starting advanced enrichment based on: {input_filepath}")
        
        # Perform advanced enrichment
        print(f"Calling perform_advanced_enrichment...")
        result_path = assistant.perform_advanced_enrichment(input_filepath)
        
        if result_path:
            print(f"Advanced enrichment completed successfully!")
            print(f"Root note created/updated at: {result_path}")
            print(f"Additional notes may have been created in: {assistant.output_dir}")
            logger.info(f"Advanced enrichment process completed successfully!")
            logger.info(f"Root note created/updated at: {result_path}")
            logger.info(f"Additional notes may have been created in: {assistant.output_dir}")
        else:
            logger.error("Advanced enrichment failed.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"An error occurred during advanced enrichment: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
