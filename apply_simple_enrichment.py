#!/usr/bin/env python3
# filepath: /home/yavuz/Projects/obsidian_suite/apply_simple_enrichment.py
"""
A simple script to apply simple enrichment to an Obsidian note.
Usage: python apply_simple_enrichment.py /path/to/note.md [/path/to/output.md]
"""

import sys
import os
from src.core.di.setup import setup_container
from src.tools.enricher.assistant import EnricherAssistant
from src.core.logging.setup import get_logger
from src.core.file_io.utils import read_file, write_file
from src.core.obsidian.parser import parse_frontmatter
from src.core.obsidian.formatter import format_note

logger = get_logger(__name__)

def main():
    """Apply simple enrichment to the specified Obsidian note."""
    if len(sys.argv) < 2:
        print("Usage: python apply_simple_enrichment.py /path/to/note.md [/path/to/output.md]")
        sys.exit(1)
    
    input_filepath = os.path.abspath(sys.argv[1])
    
    # If output file is provided, use it, otherwise overwrite the input file
    output_filepath = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else input_filepath
    
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
        
        print(f"Reading input file: {input_filepath}")
        # Read the input file
        original_content = read_file(input_filepath)
        
        # Extract frontmatter and body
        original_frontmatter = parse_frontmatter(original_content)
        
        # Extract body by removing frontmatter if it exists
        import re
        fm_match = re.match(r'^---\s*\n.*?\n---\s*\n', original_content, re.DOTALL)
        if fm_match:
            original_body = original_content[fm_match.end():]
        else:
            original_body = original_content
        
        print(f"Starting simple enrichment...")
        logger.info(f"Starting simple enrichment based on: {input_filepath}")
        
        # Perform simple enrichment
        enrichment_result = assistant.perform_simple_enrichment(original_body)
        
        if enrichment_result:
            enriched_content, concepts = enrichment_result
            print(f"Simple enrichment completed successfully!")
            logger.info(f"Simple enrichment completed successfully!")
            
            # Merge new concepts with existing ones (if any)
            existing_concepts = original_frontmatter.get('concepts', [])
            all_concepts = sorted(list(set(existing_concepts + concepts)))
            
            print(f"New concepts identified: {', '.join(concepts)}")
            
            # Format the final note using the core formatter
            final_note_content = format_note(
                content=enriched_content,
                note_type=original_frontmatter.get('type', 'note'),  # Preserve original type
                concepts=all_concepts,
                parent_note_title=original_frontmatter.get('parent')  # Preserve original parent
            )
            
            # Write the enriched content to the output file
            write_file(output_filepath, final_note_content)
            
            print(f"Enriched note saved to: {output_filepath}")
            logger.info(f"Enriched note saved to: {output_filepath}")
        else:
            print(f"Simple enrichment failed.")
            logger.error("Simple enrichment failed.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"An error occurred during simple enrichment: {e}", exc_info=True)
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
