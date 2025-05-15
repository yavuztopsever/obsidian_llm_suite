import os
import re
from typing import Dict, Any, Optional, List, Tuple

from src.core.base.assistant import BaseAssistant
from src.core.config.loader import get_config
from src.core.obsidian.parser import parse_frontmatter
from src.core.obsidian.formatter import format_note, format_obsidian_tag, format_obsidian_link
from src.core.file_io.utils import read_file, write_file
from src.core.utils.text import sanitize_filename
from src.core.schemas.enricher import EnrichmentOutput
from src.core.llm.client import LLMClient

class EnricherAssistant(BaseAssistant):
    """Handles enriching Obsidian notes using simple or advanced methods."""

    def __init__(self):
        """Initializes the EnricherAssistant."""
        super().__init__("enricher")
        
        # Load configuration
        self.simple_enrich_model = self.get_config('simple_model', 'o4-mini')  # Use a cheap reasoning model
        self.output_dir = self.get_config('output_dir', '/home/yavuz/Documents/vault')  # Default output directory
        
        # Initialize LLM client
        try:
            self.llm_client = self.initialize_llm_client("openai")
            self.log_info(f"EnricherAssistant initialized.")
            self.log_info(f"Simple enrichment model: {self.simple_enrich_model}")
        except ValueError as e:
            self.log_error(f"Failed to initialize OpenAI client for EnricherAssistant: {e}")
            raise
            
        # We'll initialize the ResearchAssistant when needed to avoid circular imports
        self.research_assistant = None

    def _parse_obsidian_content(self, content: str) -> Dict[str, Any]:
        """Parses an Obsidian note into frontmatter and body components.
        
        Args:
            content: The string content of the Obsidian note.
            
        Returns:
            A dictionary with 'frontmatter' and 'body' keys.
        """
        # Extract frontmatter
        frontmatter_data = parse_frontmatter(content)
        
        # Extract body by removing frontmatter if it exists
        fm_match = re.match(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
        if fm_match:
            body = content[fm_match.end():]
        else:
            body = content
        
        return {
            'frontmatter': frontmatter_data,
            'body': body
        }

    def perform_simple_enrichment(self, note_content: str) -> Optional[Tuple[str, List[str]]]:
        """
        Performs simple enrichment on the provided note content using an OpenAI model.

        Args:
            note_content: The Markdown content of the note to enrich.

        Returns:
            A tuple containing (enriched_content, concepts) or None if failed.
        """
        self.log_info("Performing simple enrichment...")

        # Prepare the user prompt for the LLM
        user_prompt = f"Here is the Obsidian note content to enrich:\n\n---\n{note_content}\n---"

        # Load system prompt
        system_prompt = self.load_system_prompt("simple_enrich", self._get_default_simple_enrich_system_prompt())

        # Generate JSON response
        result = self.llm_client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.simple_enrich_model,
            schema_class=EnrichmentOutput,
            temperature=0.7,  # Allow for some creativity
            max_tokens=4000  # Allow ample space for enrichment
        )

        if not result:
            self.log_error("Simple enrichment failed: Unable to get valid JSON response from LLM")
            return None

        try:
            # If result is already a validated EnrichmentOutput instance
            if isinstance(result, EnrichmentOutput):
                self.log_info("Successfully generated and validated simple enrichment output.")
                return result.enriched_content, result.concepts
            # If result is a dictionary (needs validation)
            elif isinstance(result, dict):
                validated_output = EnrichmentOutput(**result)
                self.log_info("Successfully generated and validated simple enrichment output.")
                return validated_output.enriched_content, validated_output.concepts
            else:
                self.log_error(f"Unexpected result type: {type(result)}")
                return None
        except Exception as e:
            self.log_error(f"Simple enrichment output validation failed: {e}")
            return None

    def perform_advanced_enrichment(self, note_filepath: str) -> Optional[str]:
        """
        Performs advanced enrichment on the provided note file using the ResearchAssistant.
        The generated root note will overwrite the original note file if the output directory matches.
        
        Args:
            note_filepath: Path to the note file to enrich.
            
        Returns:
            The path to the root note file created by the researcher, or None if failed.
        """
        self.log_info(f"Performing advanced enrichment based on note: {note_filepath}")
        
        # Initialize ResearchAssistant if not already done
        if self.research_assistant is None:
            from src.tools.researcher.assistant import ResearchAssistant
            # Ensure researcher uses the same output dir configured for enricher if needed,
            # or rely on researcher's own config. Assuming researcher's config is correct.
            self.research_assistant = ResearchAssistant() 
            # Check if output directories match for overwrite behavior
            if self.research_assistant.output_dir != os.path.dirname(note_filepath):
                 self.log_warning(f"Researcher output directory ('{self.research_assistant.output_dir}') differs from input note directory ('{os.path.dirname(note_filepath)}'). Original file will not be overwritten.")

        
        try:
            original_note_content = read_file(note_filepath)
            parsed_data = self._parse_obsidian_content(original_note_content)
            content_to_seed = parsed_data['body']
            # Extract the base name of the original file to use as the root name
            original_basename = os.path.splitext(os.path.basename(note_filepath))[0]
        except FileNotFoundError:
            self.log_error(f"Input note file not found: {note_filepath}")
            return None
        except Exception as e:
            self.log_error(f"Error reading or parsing input note {note_filepath}: {e}")
            return None

        # Use ResearchAssistant modularly
        planning_query = f"Existing Note Content:\n\n---\n{content_to_seed}\n---\n\nBased on the content above, generate a hierarchical plan for *new* research notes to expand on this topic. The root note should encapsulate the core theme."
        plan = self.research_assistant.plan_research_structure(planning_query)
        if not plan or len(plan) < 1: # Allow single-note generation if plan is just a root
            self.log_error("Failed to generate a valid research plan. Aborting advanced enrichment.")
            return None
        
        # Check for multi-level structure if desired (optional check)
        is_hierarchical = any(n.get('level', 0) > 0 for n in plan)
        if is_hierarchical:
             self.log_info(f"Successfully generated and validated hierarchical research plan: {len(plan)} new notes planned.")
        else:
             self.log_info(f"Successfully generated and validated research plan (single root note): {len(plan)} new note planned.")


        # Generate notes using the modular method, passing the original basename as the required root name
        # The researcher will now create the root note with the name {original_basename}.md in its output_dir
        root_note_path = self.research_assistant.generate_hierarchical_notes(plan, required_root_name=original_basename)

        if root_note_path:
            self.log_info(f"Advanced enrichment process completed. Root note generated at: {root_note_path}")
            # If researcher's output_dir is the same as the original note's dir, 
            # and required_root_name was used, the original file is effectively overwritten.
            # No need to manually link back or modify the original file here anymore.
            return root_note_path # Return the path to the *new* root note
        else:
            self.log_error("ResearchAssistant failed to generate notes.")
            return None

    def _get_default_simple_enrich_system_prompt(self) -> str:
        """Returns the default system prompt for simple enrichment."""
        return (
            """
            You are an AI assistant specializing in enhancing and expanding Obsidian notes.
            Your goal is to take the provided Markdown note content and enrich it by:
            1.  **Expanding Scope:** Add more relevant information, details, examples, or explanations.
            2.  **Improving Clarity:** Rephrase sections for better understanding, improve flow and structure.
            3.  **Adding Reasoning:** Explain concepts more thoroughly, provide justifications or connections.
            4.  **Brainstorming:** Generate related ideas or perspectives on the topic.
            5.  **Maintaining Format:** Keep the output in Markdown format, respecting existing structure where appropriate.
            6.  **Generating Concepts:** Identify key concepts or tags from the *final enriched* content.

            **Input:** You will receive the current content of an Obsidian note.

            **Output:** Respond ONLY with a valid JSON object matching the following schema:
            ```json
            {
              "enriched_content": "...", // The full, enriched Markdown content
              "concepts": ["concept1", "concept2", ...] // List of raw concept strings (no #)
            }
            ```
            Focus on making the note more valuable for learning, studying, or organization.
            Do not simply repeat the input; significantly enhance it.
            Ensure the JSON is valid and complete. Do not include any explanatory text before or after the JSON object.
            """
        )