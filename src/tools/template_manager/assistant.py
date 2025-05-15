import json
import datetime
import re
from typing import Dict, Any, Optional, List

from src.core.base.assistant import BaseAssistant
from src.core.obsidian.formatter import format_note, format_obsidian_tag, format_obsidian_link
from src.core.schemas.template_manager import TemplateOutput
from src.core.llm.client import LLMClient

class TemplateManagerAssistant(BaseAssistant):
    """Handles processing markdown notes to apply a structured template using an LLM."""

    def __init__(self):
        """Initializes the TemplateManagerAssistant."""
        super().__init__("template_manager")
        
        # Load configuration
        self.allowed_note_types = self.get_config('allowed_note_types', [
            "note", "category", "main", "sub", "sensitive", "person", "log"
        ])
        self.json_schema = self._build_json_schema()
        self.llm_model = self.get_config('llm_model', self.get_config('default_llm_model', 'gpt-4o-mini'))
        
        # Initialize LLM client
        try:
            self.llm_client = self.initialize_llm_client("openai")
            self.log_info(f"TemplateManagerAssistant initialized. Using LLM model: {self.llm_model}")
        except ValueError as e:
            self.log_error(f"Failed to initialize LLM client: {e}")
            raise

    def _build_json_schema(self) -> Dict[str, Any]:
        """Builds the JSON schema dynamically based on allowed note types."""
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The main title for the note."},
                "creation_date": {"type": "string", "description": "Creation date in ISO 8601 format (YYYY-MM-DD)."},
                "note_type": {
                    "type": "string",
                    "enum": self.allowed_note_types,
                    "description": "The primary type/category of the note."
                },
                "parent_note": {
                    "type": ["string", "null"],
                    "description": "The title of the primary parent note, if applicable (raw title, no [[ ]]). Null if no parent."
                },
                "concepts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of key concepts or keywords (raw strings, no #)."
                },
                "related_notes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of titles of other related notes (raw titles, no [[ ]]). Exclude the parent note if specified."
                },
                "summary": {"type": "string", "description": "A brief summary of the note content."},
                "content": {"type": "string", "description": "The main body content, potentially restructured or enhanced, in Markdown format."}
            },
            "required": ["title", "creation_date", "note_type", "concepts", "summary", "content"]
        }

    def _clean_llm_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cleans data received from the LLM *after* validation."""
        cleaned_data = data.copy()
        self.log_debug("Starting data cleaning.")

        # Clean Parent Note
        parent_note = cleaned_data.get('parent_note')
        cleaned_parent_note: Optional[str] = None
        if isinstance(parent_note, str):
            cleaned_title = parent_note.strip().replace('[[', '').replace(']]', '').replace('"', '').replace("'", "")
            if cleaned_title:
                cleaned_parent_note = cleaned_title
        elif parent_note is not None:
            self.log_warning(f"'parent_note' field is not a string or null: {parent_note}. Setting to null.")
        cleaned_data['parent_note'] = cleaned_parent_note
        self.log_debug(f"Cleaned parent_note: {cleaned_data['parent_note']}")

        # Clean Concepts
        concepts = cleaned_data.get('concepts', [])
        if not isinstance(concepts, list):
            self.log_warning(f"'concepts' field is not a list: {concepts}. Resetting to empty list.")
            concepts = []
        cleaned_concepts = []
        for concept in concepts:
            if isinstance(concept, str):
                cleaned_c = concept.strip().replace('#', '').replace('[', '').replace(']', '').replace('"', '').replace("'", "")
                if cleaned_c:
                    cleaned_concepts.append(cleaned_c)
            else:
                self.log_warning(f"Non-string item found in 'concepts': {concept}. Skipping.")
        cleaned_data['concepts'] = cleaned_concepts
        self.log_debug(f"Cleaned concepts: {cleaned_data['concepts']}")

        # Clean Related Notes (Ensure parent is not duplicated here if already specified)
        related_notes = cleaned_data.get('related_notes', [])
        if not isinstance(related_notes, list):
            self.log_warning(f"'related_notes' field is not a list: {related_notes}. Resetting to empty list.")
            related_notes = []
        cleaned_related = []
        for note_title in related_notes:
            if isinstance(note_title, str):
                cleaned_title = note_title.strip().replace('[[', '').replace(']]', '').replace('"', '').replace("'", "")
                # Avoid adding the parent note if it's already in the dedicated field
                if cleaned_title and cleaned_title != cleaned_parent_note:
                    cleaned_related.append(cleaned_title)
            else:
                self.log_warning(f"Non-string item found in 'related_notes': {note_title}. Skipping.")
        cleaned_data['related_notes'] = cleaned_related
        self.log_debug(f"Cleaned related_notes: {cleaned_data['related_notes']}")

        # Clean and Default Note Type
        note_type = str(cleaned_data.get('note_type', 'note')).strip()
        if note_type not in self.allowed_note_types:
            self.log_warning(f"note_type '{note_type}' is not allowed. Setting to 'note'.")
            note_type = 'note'
        if not note_type:
            self.log_warning("note_type is empty after cleaning. Setting to 'note'.")
            note_type = 'note'
        cleaned_data['note_type'] = note_type
        self.log_debug(f"Cleaned note_type: {cleaned_data['note_type']}")

        # Clean and Default Title
        title = str(cleaned_data.get('title', 'Untitled Note')).strip()
        if not title:
            self.log_warning("title is empty after cleaning. Setting to 'Untitled Note'.")
            title = 'Untitled Note'
        cleaned_data['title'] = title
        self.log_debug(f"Cleaned title: {cleaned_data['title']}")

        # Clean and Default Summary
        summary = str(cleaned_data.get('summary', 'No summary provided.')).strip()
        cleaned_data['summary'] = summary
        self.log_debug(f"Cleaned summary: {cleaned_data['summary']}")

        # Clean and Default Content (Don't strip leading/trailing whitespace)
        content = str(cleaned_data.get('content', 'No content provided.'))
        cleaned_data['content'] = content

        self.log_info("Data cleaning finished.")
        return cleaned_data

    def _format_note_content(self, data: Dict[str, Any]) -> str:
        """Formats the cleaned data into the final Obsidian note structure using a metadata block."""
        self.log_debug("Starting note formatting with metadata block.")

        # Extract metadata
        note_type = data.get("note_type", "note") # Default to 'note'
        concepts = data.get("concepts", []) # Default to empty list
        parent_note_title: Optional[str] = data.get("parent_note")
        related_notes_titles: List[str] = data.get("related_notes", []) # Extract related notes

        if parent_note_title:
            self.log_debug(f"Using '{parent_note_title}' as parent_note_title from dedicated field.")
        else:
            self.log_debug("No parent_note_title specified.")
        self.log_debug(f"Using related_notes_titles: {related_notes_titles}")

        # Construct the main content body
        title = data.get("title", "Untitled Note")
        summary = data.get("summary", "No summary provided.")
        content = data.get("content", "No content provided.")

        # Basic structure for the main content part
        main_content_body = f"""
# {title}

## Summary
{summary}

## Content
{content}
"""

        # Use the format_note function from the formatter module, passing related notes
        final_content = format_note(
            content=main_content_body.strip(),
            note_type=note_type,
            concepts=concepts,
            parent_note_title=parent_note_title,
            related_notes_titles=related_notes_titles # Pass the related notes list
        )

        self.log_info("Note formatting with metadata block finished.")
        return final_content.strip()

    def process_note_content(self, note_content: str) -> Optional[str]:
        """Processes the raw content of a single note.

        Args:
            note_content: The raw string content of the markdown note.

        Returns:
            The processed and formatted note content as a string, or None if processing fails.
        """
        # ADDED: Log the very start of processing with a unique identifier if possible (e.g., first few chars)
        processing_id = note_content[:30].replace('\n', ' ') # Simple identifier
        self.log_info(f"[{processing_id}] Starting processing...")
        self.log_debug(f"[{processing_id}] Received note_content (first 100 chars): {note_content[:100]}...")

        # Prepare prompts
        system_prompt = self.load_system_prompt("template", self._get_default_system_prompt())
        # MODIFIED: Directly generate the user prompt for the current content,
        # bypassing potential caching in load_user_prompt
        user_prompt = self._get_default_user_prompt(note_content)

        # ADDED: Log the generated user prompt before sending
        self.log_debug(f"[{processing_id}] Generated user_prompt (first 200 chars): {user_prompt[:200]}...")

        # Send to LLM
        self.log_debug(f"[{processing_id}] Sending request to LLM (model: {self.llm_model})...")
        llm_response_data = self.llm_client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.llm_model
        )

        # ADDED: Log the raw LLM response
        self.log_debug(f"[{processing_id}] Raw LLM response data: {llm_response_data}")

        if llm_response_data is None:
            self.log_error(f"[{processing_id}] Failed to get a valid response from LLM.")
            return None

        # Validate JSON structure
        if not hasattr(self, '_schema_validator'):
             from src.core.schemas.validator import SchemaValidator
             self._schema_validator = SchemaValidator()

        if not self._schema_validator.validate_with_jsonschema(llm_response_data, self.json_schema):
            self.log_error(f"[{processing_id}] LLM response failed JSON schema validation.")
            self.log_debug(f"[{processing_id}] Invalid LLM response data: {llm_response_data}")
            return None
        self.log_info(f"[{processing_id}] LLM response passed JSON schema validation.")

        # Clean LLM data
        cleaned_data = self._clean_llm_data(llm_response_data)
        # ADDED: Log the cleaned data
        self.log_debug(f"[{processing_id}] Cleaned data: {cleaned_data}")

        # Format into final note structure
        formatted_content = self._format_note_content(cleaned_data)
        # ADDED: Log the final formatted content before returning
        self.log_debug(f"[{processing_id}] Formatted content before returning (first 100 chars): {formatted_content[:100]}...")

        self.log_info(f"[{processing_id}] Note content processed successfully.")
        return formatted_content
        
    def _get_default_system_prompt(self) -> str:
        """Returns the default system prompt if not found in config."""
        return (
            """
            You are an expert assistant specialized in processing markdown notes for Obsidian vault creation.
            Analyze the provided note content, focusing **strictly on existing [[wikilinks]]** to generate a structured JSON object following the schema.

            Key tasks:
            1.  Generate a concise 'summary'.
            2.  Identify the single most likely 'parent_note' title **exclusively from [[wikilinks]]** found in the content (raw string, null if none). If multiple wikilinks exist, choose the most plausible parent.
            3.  List other 'related_notes' titles **exclusively from the remaining [[wikilinks]]** in the content (raw strings, exclude the chosen parent).
            4.  List key 'concepts' (raw strings, can be inferred from text).
            5.  Structure the main 'content' using markdown.
            6.  Determine the 'note_type' from the allowed list (raw string).
            7.  Extract the 'title' and 'creation_date' (ISO 8601).

            Provide RAW string values ONLY in the JSON. Do NOT include any Obsidian markdown formatting (#, [[ ]], quotes, extra brackets) within JSON values for 'parent_note', 'note_type', 'concepts', or 'related_notes'.
            Ensure the final JSON is valid and strictly adheres to the schema. **Only use titles explicitly mentioned within [[wikilinks]] in the source content for the 'parent_note' and 'related_notes' fields.**
            """
        )

    def _get_default_user_prompt(self, note_content: str) -> str:
        """Returns the default user prompt template with the provided note content."""
        # Rebuild schema string in case it changed
        schema_string = json.dumps(self._build_json_schema(), indent=2)
        return (
            f"""
            Process the following markdown note content into a JSON object according to the schema.
            Analyze the text carefully. **Strictly use only the titles found within explicit [[wikilinks]]** in the content to determine the 'parent_note' and 'related_notes' fields.
            - For 'parent_note', select the single most likely parent title from the [[wikilinks]] (use null if no suitable wikilink exists).
            - For 'related_notes', list the titles from any other [[wikilinks]] found in the content (excluding the one chosen as parent).
            Provide RAW string values for parent_note, related_notes, concepts, and note_type (no [[ ]], #, etc.).

            Schema:
            {schema_string}

            Note content:
            ---
            {note_content}
            ---
            """
        )