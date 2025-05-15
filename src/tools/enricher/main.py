# src/tools/enricher/main.py
import argparse
import os
import sys

# Core library imports
from src.core.logging.setup import get_logger
from src.core.file_io.utils import read_file, write_file
from src.core.obsidian.parser import parse_frontmatter
from src.core.obsidian.formatter import format_note
from src.core.di.setup import setup_container
from src.core.di.container import ServiceContainer

# Tool specific imports
from src.tools.enricher.assistant import EnricherAssistant

logger = get_logger(__name__)

def main():
    """Main function to run the Enricher tool."""
    parser = argparse.ArgumentParser(description="Enrich an Obsidian note using AI.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["simple", "advanced"],
        required=True,
        help="Enrichment mode: 'simple' (enhance existing note) or 'advanced' (generate hierarchical research based on note)."
    )
    parser.add_argument(
        "--input-file",
        type=str,
        required=True,
        help="Path to the input Obsidian note file (.md)."
    )
    parser.add_argument(
        "--output-file",
        type=str,
        help="Path to the output file (optional). For 'simple' mode, defaults to overwriting the input file. Ignored for 'advanced' mode."
    )

    args = parser.parse_args()

    input_filepath = os.path.abspath(args.input_file)
    output_filepath = os.path.abspath(args.output_file) if args.output_file else input_filepath

    if not os.path.exists(input_filepath):
        logger.error(f"Input file not found: {input_filepath}")
        sys.exit(1)

    if args.mode == "simple" and not args.output_file:
        logger.warning(f"No output file specified for simple mode. Input file '{input_filepath}' will be overwritten.")

    if args.mode == "advanced" and args.output_file:
        logger.warning("Output file argument is ignored in 'advanced' mode. New notes are created in the configured researcher output directory.")

    try:
        # Initialize the dependency injection container
        setup_container()
        
        # Get the EnricherAssistant from the container or create a new one if not registered
        if ServiceContainer.has("enricher"):
            assistant = ServiceContainer.get("enricher")
        else:
            assistant = EnricherAssistant()
            ServiceContainer.register("enricher", assistant)
    except Exception as e:
        logger.error(f"Failed to initialize EnricherAssistant: {e}", exc_info=True)
        sys.exit(1)

    if args.mode == "simple":
        logger.info(f"Starting simple enrichment for: {input_filepath}")
        try:
            original_content = read_file(input_filepath)
            
            # Extract frontmatter and body separately
            original_frontmatter = parse_frontmatter(original_content)
            
            # Extract body by removing frontmatter if it exists
            import re
            fm_match = re.match(r'^---\s*\n.*?\n---\s*\n', original_content, re.DOTALL)
            if fm_match:
                original_body = original_content[fm_match.end():]
            else:
                original_body = original_content

            enrichment_result = assistant.perform_simple_enrichment(original_body)

            if enrichment_result:
                enriched_content, concepts = enrichment_result
                logger.info("Simple enrichment successful.")

                # Merge new concepts with existing ones (if any)
                existing_concepts = original_frontmatter.get('concepts', [])
                all_concepts = sorted(list(set(existing_concepts + concepts)))

                # Format the final note using the core formatter
                final_note_content = format_note(
                    content=enriched_content,
                    note_type=original_frontmatter.get('type', 'note'), # Preserve original type
                    concepts=all_concepts,
                    parent_note_title=original_frontmatter.get('parent') # Preserve original parent
                )

                # Write the enriched content to the output file
                write_file(output_filepath, final_note_content)
                logger.info(f"Enriched note saved to: {output_filepath}")
            else:
                logger.error("Simple enrichment failed.")
                sys.exit(1)

        except FileNotFoundError:
            logger.error(f"Input file not found during processing: {input_filepath}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"An error occurred during simple enrichment: {e}", exc_info=True)
            sys.exit(1)

    elif args.mode == "advanced":
        logger.info(f"Starting advanced enrichment based on: {input_filepath}")
        try:
            # Advanced enrichment handles file reading/writing internally via the researcher
            # It modifies the original note and creates new ones in the researcher's dir
            result_path = assistant.perform_advanced_enrichment(input_filepath)

            if result_path:
                logger.info(f"Advanced enrichment process completed. Original note '{result_path}' may have been updated with links. New research notes created in '{assistant.output_dir}'.")
            else:
                logger.error("Advanced enrichment failed.")
                sys.exit(1)

        except Exception as e:
            logger.error(f"An error occurred during advanced enrichment: {e}", exc_info=True)
            sys.exit(1)

if __name__ == "__main__":
    main()