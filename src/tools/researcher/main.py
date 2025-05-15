# src/tools/researcher/main.py
import argparse
import sys
import os
import yaml  # Added for YAML parsing
from typing import Dict, Any, Optional, List # Added List

# Core components
from src.core.di.setup import setup_container
from src.core.logging.setup import setup_logging, get_logger
from src.tools.researcher.assistant import ResearchAssistant
from src.core.utils.document_parser import parse_document # Added document parser
from src.core.file_io.utils import read_file, write_file # Ensure read_file is imported

# Setup logging
setup_logging()
logger = get_logger(__name__)

DEFAULT_QUERY_YAML = "/home/yavuz/Projects/obsidian_suite/src/tools/researcher/research_query.yaml"

def load_research_input(file_path: str) -> Optional[Dict[str, Any]]:
    """Loads research query and context paths from a YAML file."""
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        if data and 'research_query' in data:
            return data['research_query']
        else:
            logger.error(f"Invalid YAML structure in {file_path}. Missing 'research_query' key.")
            return None
    except FileNotFoundError:
        logger.error(f"Input YAML file not found: {file_path}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading YAML file {file_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Run the research assistant.")
    # Make input_file optional, provide default
    parser.add_argument("--input-file", type=str, default=DEFAULT_QUERY_YAML,
                        help=f"Path to the input file (YAML or text). Defaults to {DEFAULT_QUERY_YAML}")
    args = parser.parse_args()

    # Setup dependency injection container
    container = setup_container()
    if container is None:
        logger.error("Dependency injection container setup failed. Exiting.")
        sys.exit(1)

    # Retrieve assistant using the string key used during registration
    assistant = container.get("researcher") # Changed from ResearchAssistant to "researcher"
    if assistant is None:
        logger.error("Failed to retrieve ResearchAssistant from container. Exiting.")
        sys.exit(1)

    try:
        # Determine input type and load query/context
        input_file_path = args.input_file
        query_text: Optional[str] = None
        extra_context_paths: List[str] = []
        required_root_name: Optional[str] = None # Optional: For naming the root note

        if input_file_path.lower().endswith(".yaml"):
            logger.info(f"Loading research input from YAML: {input_file_path}")
            research_input = load_research_input(input_file_path)
            if not research_input:
                sys.exit(1) # Exit if YAML loading failed

            query_text = research_input.get("query")
            extra_context_paths = research_input.get("extra_context_document_paths", [])
            required_root_name = research_input.get("required_root_file_name") # Get optional root name

            if not query_text:
                logger.error("YAML file must contain a 'query' field.")
                sys.exit(1)

        else: # Assume plain text file containing only the query
             logger.info(f"Loading research query from text file: {input_file_path}")
             # Use core read_file utility - assumes it returns string or None
             try:
                 with open(input_file_path, 'r', encoding='utf-8') as f:
                     query_text = f.read()
             except FileNotFoundError:
                 logger.error(f"Input text file not found: {input_file_path}")
                 sys.exit(1)
             except Exception as e:
                 logger.error(f"Error reading text file {input_file_path}: {e}")
                 sys.exit(1)
             
             if not query_text:
                 logger.error(f"Query text file is empty: {input_file_path}")
                 sys.exit(1)

        # --- Parse extra context documents ---
        parsed_context = ""
        if extra_context_paths:
            logger.info(f"Parsing {len(extra_context_paths)} extra context document(s)...")
            for doc_path in extra_context_paths:
                # Ensure path is absolute or resolve relative to YAML location if needed
                absolute_doc_path = os.path.abspath(os.path.join(os.path.dirname(input_file_path), doc_path)) if not os.path.isabs(doc_path) and input_file_path.lower().endswith(".yaml") else doc_path
                logger.info(f"Parsing: {absolute_doc_path}")
                content = parse_document(absolute_doc_path)
                if content:
                    # Add separator and filename for clarity in the prompt
                    parsed_context += f"\n\n--- Context from {os.path.basename(doc_path)} ---\n{content}"
                else:
                    logger.warning(f"Could not parse context document: {absolute_doc_path}")

        # --- Combine query and context for planning ---
        final_planner_prompt = query_text
        if parsed_context:
            final_planner_prompt += f"\n\n--- Additional Context ---\n{parsed_context}"
            logger.info("Added parsed context to the planning prompt.")

        logger.info(f"Starting research process based on query and context from: {input_file_path}")

        # --- Stage 1: Plan the research structure ---
        logger.info("Stage 1: Planning research structure...")
        # Pass the combined prompt to the planner
        research_plan = assistant.plan_research_structure(final_planner_prompt)

        if not research_plan:
            logger.error("Failed to generate research plan. Exiting.")
            sys.exit(1)

        logger.info(f"Stage 1: Research plan generated with {len(research_plan)} notes.")

        # --- Stage 2: Generate hierarchical notes based on the plan ---
        logger.info("Stage 2: Generating hierarchical notes...")
        # Pass the original plan (list of dicts) and the required root name
        result_path = assistant.generate_hierarchical_notes(research_plan, required_root_name=required_root_name) # Pass plan

        if result_path:
            logger.info(f"Research process completed. Root note saved to: {result_path}")
            print(f"New research notes created in: {os.path.dirname(result_path)}")
        else:
            logger.error("Failed to generate hierarchical notes.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"An error occurred during research process: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        sys.exit(1)

if __name__ == "__main__":
    main()
