import json
import datetime
import os
import re
from typing import Dict, Any, Optional, List, Tuple

from src.core.base.assistant import BaseAssistant
from src.core.obsidian.formatter import format_obsidian_link, format_note, format_obsidian_tag
from src.core.utils.text import sanitize_filename
from src.core.file_io.utils import read_file, write_file
from src.core.schemas.researcher import ResearchNote, ResearchStructure, GeneratedNoteContent

class ResearchAssistant(BaseAssistant):
    """Handles conducting research using LLMs and formatting the results as Obsidian notes."""

    def __init__(self):
        """Initializes the ResearchAssistant."""
        super().__init__("researcher")
        
        # Load configuration
        self.openai_model = self.get_config('openai_model', 'o4-mini')
        self.perplexity_model = self.get_config('perplexity_model', 'sonar-pro')
        self.output_dir = self.get_config('output_dir', '/home/yavuz/Documents/vault')
        self.request_timeout = int(self.get_config('request_timeout', 180))
        
        # Initialize LLM clients
        try:
            self.openai_client = self.initialize_llm_client("openai")
            self.perplexity_client = self.initialize_llm_client("perplexity")
            
            self.log_info(f"ResearchAssistant initialized with two-stage process")
            self.log_info(f"Stage 1: OpenAI planning using model: {self.openai_model}")
            self.log_info(f"Stage 2: Perplexity content generation using model: {self.perplexity_model}")
            self.log_info(f"Output directory: {self.output_dir}")
            self.log_info(f"Request timeout: {self.request_timeout}s")
        except ValueError as e:
            self.log_error(f"Failed to initialize LLM clients: {e}")
            raise

    def generate_content_for_note(self, instructions: str) -> Optional[GeneratedNoteContent]:
        """Stage 2: Generates content and concepts for a single note using Perplexity based on instructions.
        
        Args:
            instructions: The instructions for generating the note content.
            
        Returns:
            The generated note content, or None if generation failed.
        """
        self.log_info("Stage 2: Generating content with Perplexity...")
        user_prompt = f"Please generate the content based on the following instructions:\n\n---\n{instructions}\n---"

        # Define web search options (can be made configurable if needed)
        web_search_options = {
            "search_context_size": "high" # Or "default", "low"
        }
        
        # Get the content generation system prompt
        system_prompt = self.load_system_prompt("content_gen", self._get_default_content_gen_system_prompt())
        
        # Generate the content using Perplexity
        json_schema = GeneratedNoteContent.model_json_schema()
        
        result = self.perplexity_client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=json_schema,
            schema_class=GeneratedNoteContent,
            model=self.perplexity_model,
            timeout=self.request_timeout,
            web_search_options=web_search_options,
            schema_name="generated_note_content",
            schema_description="Structured output containing generated markdown content and relevant concepts."
        )

        if not result:
            self.log_error("Perplexity content generation failed")
            return None

        self.log_info("Successfully generated and validated content from Perplexity.")
        return result

    def generate_hierarchical_notes(self, research_plan: List[Dict[str, Any]], required_root_name: Optional[str] = None) -> Optional[str]:
        """Processes the research plan (Stage 1), generates content for each note (Stage 2),
           creates hierarchical Obsidian notes, and returns the filename of the root note.

        Args:
            research_plan: The research plan generated in Stage 1.
            required_root_name: Optional preferred basename for the root note file.

        Returns:
            The path to the root note file, or None if generation failed.
        """
        if not research_plan:
            self.log_error("Cannot generate notes from empty research plan list.")
            return None

        self.log_info(f"Processing {len(research_plan)} notes from research plan for hierarchical file generation.")

        # Convert Pydantic models from planning stage to dictionaries if needed
        processed_plan = []
        for note_plan in research_plan:
            if hasattr(note_plan, 'dict') and callable(getattr(note_plan, 'dict')):
                processed_plan.append(note_plan.dict())
            elif hasattr(note_plan, 'model_dump') and callable(getattr(note_plan, 'model_dump')):
                processed_plan.append(note_plan.model_dump())
            else:
                processed_plan.append(note_plan)

        notes_by_id = {note['id']: note for note in processed_plan}
        children_by_parent_id = {}
        root_notes = []

        # Build hierarchy structure and identify roots
        for note_id, note_plan in notes_by_id.items():
            parent_id = note_plan.get('parent_id')
            if parent_id is None:
                root_notes.append(note_plan)
            else:
                if parent_id not in children_by_parent_id:
                    children_by_parent_id[parent_id] = []
                if parent_id in notes_by_id:
                    children_by_parent_id[parent_id].append(note_plan)
                else:
                    self.log_warning(f"Note '{note_plan.get('title', note_id)}' has non-existent parent_id '{parent_id}'. Skipping.")

        # --- Check for single root ---
        if len(root_notes) == 1:
            actual_root_node_plan = root_notes[0]
            self.log_info(f"Found single root node plan as expected: {actual_root_node_plan.get('title')}")
        elif len(root_notes) > 1:
            self.log_error(f"LLM generated {len(root_notes)} root node plans, but only one was expected. Using the first one found: '{root_notes[0].get('title')}'.")
            actual_root_node_plan = root_notes[0]
        else:
            self.log_error("No root node plan (parent_id=null) found in the research plan. Cannot generate hierarchy.")
            return None
        # --- End root check ---

        # --- Determine Root Basename ---
        # Use required_root_name if provided, otherwise sanitize the root plan's title
        root_basename_override = sanitize_filename(required_root_name) if required_root_name else None

        os.makedirs(self.output_dir, exist_ok=True)
        created_files = {}
        processed_notes = set()

        # Recursive function to create files
        def _create_note_file(note_plan_data: Dict[str, Any], parent_basename: Optional[str] = None, is_root: bool = False):
            note_id = note_plan_data['id']
            if note_id in processed_notes:
                return created_files.get(note_id)

            title = note_plan_data.get("title", f"Untitled Note {note_id}")
            instructions = note_plan_data.get("instructions", "No instructions provided.") # Instructions from Stage 1

            # --- Stage 2: Generate Content using Perplexity ---
            generated_content_obj = self.generate_content_for_note(instructions)

            if not generated_content_obj:
                self.log_error(f"Failed to generate content for note '{title}' (ID: {note_id}). Skipping file creation.")
                return None

            # Extract data from the validated content object
            generated_content = generated_content_obj.content
            generated_concepts = generated_content_obj.concepts
            generated_sources = generated_content_obj.sources or [] # Ensure it's a list

            # --- Filename and Path Construction ---
            sanitized_title = sanitize_filename(title)
            if is_root and root_basename_override:
                current_basename = root_basename_override # Use override for root
                self.log_info(f"Using required root name override: {current_basename}")
            elif parent_basename:
                current_basename = f"{parent_basename}_{sanitized_title}"
            else: # Root note without override
                current_basename = sanitized_title
            filename = f"{current_basename}.md"
            filepath = os.path.join(self.output_dir, filename)

            # --- Metadata and Linking ---
            parent_note_title = parent_basename # Use parent's basename for linking
            note_type = "note" # Default type

            # --- Content Construction ---
            # Format sources from Perplexity output
            sources_md = "".join([f"- [{src.get('title', 'Source')}]({src.get('url')})\n" for src in generated_sources if src.get('url')])
            sources_section = f"\n## Sources\n{sources_md}" if sources_md else ""

            # Find and format children links (recursive calls happen here)
            child_notes_plans = children_by_parent_id.get(note_id, [])
            child_links_md = ""
            if child_notes_plans:
                child_links_list = []
                sorted_children_plans = sorted(child_notes_plans, key=lambda x: x.get('title', ''))
                for child_plan in sorted_children_plans:
                    child_file_info = _create_note_file(child_plan, current_basename) # Recursive call
                    if child_file_info:
                        child_links_list.append(f"- {format_obsidian_link(child_file_info['basename'])}")

                if child_links_list:
                    child_links_md = "\n## Sub-Topics\n" + "\n".join(child_links_list)

            # Construct the main note body using generated content
            main_content_body = f"""
# {title}

{generated_content}
{sources_section}
{child_links_md}
"""

            # --- Format final note using the formatter ---
            final_content = format_note(
                content=main_content_body.strip(),
                note_type=note_type,
                concepts=generated_concepts, # Use concepts from Perplexity
                parent_note_title=parent_note_title
            )

            # --- Write File ---
            try:
                write_file(filepath, final_content) # Use core write_file util
                self.log_info(f"Successfully created note file: {filepath}")
                file_info = {"filepath": filepath, "basename": current_basename}
                created_files[note_id] = file_info
                processed_notes.add(note_id)
                return file_info
            except IOError as e:
                self.log_error(f"Failed to write note file {filepath}: {e}")
                return None
            except Exception as e:
                self.log_error(f"Unexpected error writing file {filepath}: {e}")
                return None

        # Start the recursive file creation process from the root plan
        root_file_info = _create_note_file(actual_root_node_plan, is_root=True) # Pass is_root=True

        return root_file_info["filepath"] if root_file_info else None

    def plan_research_structure(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Stage 1: Uses OpenAI to plan the research structure and generate instructions.
        
        Args:
            query: The research query or topic.
            
        Returns:
            The research plan as a list of note dictionaries, or None if planning or validation failed.
        """
        self.log_info(f"Planning research structure for query: '{query}'")
        
        # Get the planning system prompt
        system_prompt = self.load_system_prompt("planning", self._get_default_planning_system_prompt())
        
        # Define the Pydantic schema for the expected output (list of notes)
        # We need the top-level structure to be a list, so we use ResearchStructure which contains List[ResearchNote]
        planning_schema = ResearchStructure 

        # Generate the research plan using OpenAI - Expecting a JSON list directly via structured output
        # Increase max_tokens significantly for potentially complex plans
        PLANNING_MAX_TOKENS = 32000 # Increased token limit based on o4-mini capabilities
        # Use the unified generate_json method of the LLMClient instance
        result = self.openai_client.generate_json(
            system_prompt=system_prompt,
            user_prompt=query,
            schema_class=planning_schema, # Pass the Pydantic class for structured output
            model=self.openai_model, # Use the configured OpenAI model
            max_tokens=PLANNING_MAX_TOKENS # Explicitly set max tokens for planning
        )
        
        if not result:
            self.log_error("OpenAI planning stage failed to return a valid response or structure.")
            return None
        
        # --- Validation & Return --- 
        # generate_json_response should have already returned a validated Pydantic object (ResearchStructure)
        # or None if validation failed internally.
        if isinstance(result, ResearchStructure):
            notes_list = result.notes
            
            # Calculate the hierarchy depth and note count
            hierarchy_depth = 0
            if notes_list:
                 hierarchy_depth = max(note.level for note in notes_list)
            note_count = len(notes_list)
            
            # Validate against the requirements
            min_depth = 3
            max_depth = 5
            min_notes = 10
            max_notes = 15
            
            self.log_info(f"Research plan generated: {note_count} notes, hierarchy depth {hierarchy_depth}")
            
            # Check if the plan meets the requirements
            if note_count < min_notes or note_count > max_notes:
                self.log_warning(f"Research plan has {note_count} notes, which is outside the target range of {min_notes}-{max_notes}. "
                                f"Proceeding anyway, but consider regenerating for better results.")
            
            if hierarchy_depth < min_depth - 1 or hierarchy_depth > max_depth - 1:  # -1 because levels start from 0
                self.log_warning(f"Research plan has hierarchy depth of {hierarchy_depth+1} levels, which is outside the target range of {min_depth}-{max_depth} levels. "
                                f"Proceeding anyway, but consider regenerating for better results.")
                
            # Return the list of note dictionaries
            return [note.model_dump() for note in notes_list]
        else:
            # This case should ideally not be reached if generate_json_response works correctly
            self.log_error(f"OpenAI planning stage returned unexpected type {type(result)} after structured output attempt.")
            return None

    def _get_default_planning_system_prompt(self) -> str:
        """Returns the default planning system prompt."""
        return (
            """
            You are a research planning assistant. Your task is to create a **deep hierarchical research plan** based on the user's query. 
            Output this plan as a **JSON array** `[...]` containing note objects.

            **STRICT REQUIREMENTS:**
            - Create a DEEP hierarchy with **3-5 levels** (including the root level 0)
            - Generate a TOTAL of **10-15 notes** (including the root)
            - Ensure the hierarchy is balanced and logical

            **Instructions:**
            1.  Analyze the user query: `{{user_prompt}}`
            2.  Break down the main topic into logical sub-topics, focusing on DEPTH rather than BREADTH
            3.  Organize these topics into a tree structure (hierarchy) with a single root note
            4.  Ensure paths from the root to the deepest leaves are 3-5 levels deep (root=0, deepest=3-4)
            5.  For EACH note, write detailed `instructions` for a subsequent AI to generate content for that specific topic
            6.  Assign a unique `id`, the correct `parent_id` (null for root), and the correct `level` (0 for root, 1 for children, etc.) to each note
            7.  IMPORTANT: Keep the TOTAL number of notes between 10-15 (INCLUDING the root)

            **Output Format: CRITICAL**
            - Your entire output MUST be a single JSON **ARRAY** (list) starting with `[` and ending with `]`
            - **DO NOT output a JSON object `{...}`**
            - Each element in the array MUST be a note object with the following exact fields:
                - `id` (string): Unique ID (e.g., "root", "topic1", "topic1-sub1")
                - `title` (string): Note title
                - `instructions` (string): Detailed content generation instructions (Markdown allowed)
                - `parent_id` (string | null): ID of the parent note (null ONLY for the root)
                - `level` (integer): Hierarchy level (0 for root)
            - Ensure `parent_id` references an existing `id` in the array
            - Ensure `level` is `parent_level + 1`
            - Prioritize DEPTH over BREADTH - aim for paths that are at least 3 levels deep from root

            **Example Snippet (Your output must be an array like this with DEEP paths):**
            ```json
            [
              { "id": "root", "title": "Main Topic", "instructions": "...", "parent_id": null, "level": 0 },
              { "id": "sub1", "title": "Sub Topic 1", "instructions": "...", "parent_id": "root", "level": 1 },
              { "id": "sub1.1", "title": "Sub-Sub Topic 1.1", "instructions": "...", "parent_id": "sub1", "level": 2 },
              { "id": "sub1.1.1", "title": "Deep Topic 1.1.1", "instructions": "...", "parent_id": "sub1.1", "level": 3 },
              { "id": "sub1.1.2", "title": "Deep Topic 1.1.2", "instructions": "...", "parent_id": "sub1.1", "level": 3 },
              { "id": "sub2", "title": "Sub Topic 2", "instructions": "...", "parent_id": "root", "level": 1 },
              { "id": "sub2.1", "title": "Sub-Sub Topic 2.1", "instructions": "...", "parent_id": "sub2", "level": 2 }
            ]
            ```

            **Output ONLY the JSON array.** No explanations before or after.
            """
        )

    def _get_default_content_gen_system_prompt(self) -> str:
        """Returns the default content generation system prompt."""
        return (
            """
            You are a research assistant. Your task is to generate comprehensive and well-structured content based on the provided instructions.
            Use your online capabilities to research the topic thoroughly.

            **Instructions:**
            1.  **Follow the User's Instructions:** Adhere strictly to the detailed instructions provided in the user prompt.
            2.  **Generate Markdown Content:** Create the main content in well-formatted Markdown. Use headings (#, ##), lists, code blocks, bold/italic text, etc., as appropriate.
            3.  **Identify Key Concepts:** Extract a list of the most important concepts or keywords discussed in the generated content. Provide these as raw strings (no '#').
            4.  **Cite Sources (If Applicable):** If you use external web sources, provide a list of them with titles and URLs.
            5.  **Output Format:** Respond ONLY with a valid JSON object matching the following schema:
                ```json
                {
                  "content": "...", // Your generated Markdown content here
                  "concepts": ["concept1", "concept2", ...], // List of raw concept strings
                  "sources": [{"title": "Source Title", "url": "Source URL"}, ...] // Optional list of sources
                }
                ```
            Ensure the JSON is valid and complete. Do not include any explanatory text before or after the JSON object.
            """
        )
