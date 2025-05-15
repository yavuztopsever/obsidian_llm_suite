import json
import re
from typing import Set, Dict, Optional, List

from src.core.base.assistant import BaseAssistant
from src.core.obsidian.parser import extract_tags
from src.core.obsidian.formatter import format_obsidian_tag
from src.core.schemas.tag_manager import TagStandardizationMap
from src.core.llm.client import LLMClient

class TagManagerAssistant(BaseAssistant):
    """Handles finding, standardizing, and updating tags in Obsidian notes."""

    def __init__(self):
        """Initializes the TagManagerAssistant."""
        super().__init__("tag_manager")
        
        # Load configuration
        self.exempt_tags = set(self.get_config('exempt_tags', [
            "#note", "#category", "#main", "#sub", "#sensitive", "#person", "#log"
        ]))
        self.llm_model = self.get_config('llm_model', self.get_config('default_llm_model', 'gpt-4.1-nano'))
        
        # Initialize LLM client
        try:
            self.llm_client = self.initialize_llm_client("openai")
            self.log_info(f"TagManagerAssistant initialized. Using LLM model: {self.llm_model}")
            self.log_info(f"Exempt tags: {self.exempt_tags}")
        except ValueError as e:
            self.log_error(f"Failed to initialize LLM client: {e}")
            raise

    def find_tags_in_content(self, content: str) -> Set[str]:
        """Finds all unique tags in a given string content using the core parser.
        
        Args:
            content: The content to search for tags.
            
        Returns:
            A set of unique tags found in the content.
        """
        return extract_tags(content)

    def get_standardization_map(self, all_tags: Set[str]) -> Optional[Dict[str, str]]:
        """Gets the tag standardization map from the LLM.

        Args:
            all_tags: A set of all unique tags found in the vault.

        Returns:
            A dictionary mapping original tags to standardized tags, or None on failure.
        """
        tags_to_process = sorted([tag for tag in all_tags if tag not in self.exempt_tags])

        if not tags_to_process:
            self.log_info("No non-exempt tags found to send to LLM for standardization.")
            return {} # Return empty map, no standardization needed

        self.log_info(f"Sending {len(tags_to_process)} non-exempt tags to LLM for standardization...")

        # Prepare prompts
        system_prompt = self.load_system_prompt("standardization", self._get_default_system_prompt())
        tags_json = json.dumps(tags_to_process, indent=2)
        user_prompt = self.load_user_prompt("standardization", self._get_default_user_prompt()).format(tags_json=tags_json)

        # Send to LLM
        llm_response_data = self.llm_client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.llm_model,
            max_tokens=8000 # Increased max_tokens further
        )

        if llm_response_data is None:
            self.log_error("Failed to get a valid response from LLM for tag standardization.")
            return None

        # --- Validation and Cleaning of LLM Response ---
        standardization_map: Dict[str, str] = {}
        if not isinstance(llm_response_data, dict):
            self.log_error(f"LLM response for tags is not a dictionary: {llm_response_data}")
            return None

        missing_in_response = []
        invalid_format = []

        for original_tag in tags_to_process:
            if original_tag not in llm_response_data:
                missing_in_response.append(original_tag)
                standardization_map[original_tag] = format_obsidian_tag(original_tag) # Self-standardize if missing
                continue

            master_tag_raw = llm_response_data[original_tag]
            if not isinstance(master_tag_raw, str):
                self.log_warning(f"Master tag for '{original_tag}' is not a string: {master_tag_raw}. Self-standardizing.")
                standardization_map[original_tag] = format_obsidian_tag(original_tag)
                continue

            # Apply formatting rules to the LLM's proposed master tag
            master_tag_formatted = format_obsidian_tag(master_tag_raw)

            if not master_tag_formatted:
                self.log_warning(f"Master tag for '{original_tag}' ('{master_tag_raw}') became empty after formatting. Self-standardizing.")
                standardization_map[original_tag] = format_obsidian_tag(original_tag)
                continue

            # Check if the formatted tag follows basic rules (starts with #)
            if not master_tag_formatted.startswith('#'):
                invalid_format.append((original_tag, master_tag_formatted))
                standardization_map[original_tag] = format_obsidian_tag(original_tag) # Self-standardize on invalid format
            else:
                standardization_map[original_tag] = master_tag_formatted

        if missing_in_response:
            self.log_warning(f"LLM response was missing mappings for {len(missing_in_response)} tags: {missing_in_response}. They were self-standardized.")
        if invalid_format:
            self.log_warning(f"LLM provided {len(invalid_format)} master tags with invalid format (e.g., missing #): {invalid_format}. They were self-standardized.")

        self.log_info("Successfully received and processed standardization map from LLM.")
        return standardization_map

    def standardize_tags_in_content(self, content: str, standardization_map: Dict[str, str]) -> Optional[str]:
        """Replaces tags in the given content based on the standardization map.

        Args:
            content: The original file content.
            standardization_map: The map of {old_tag: new_tag}.

        Returns:
            The modified content if changes were made, otherwise None.
        """
        if not standardization_map:
            self.log_debug("No standardization map provided or map is empty. No changes needed.")
            return None

        modified_content = content
        changes_made = False

        # Filter out exempt tags from the map keys we iterate over
        tags_to_replace = {k: v for k, v in standardization_map.items() if k not in self.exempt_tags}

        # Replace longer tags first to avoid partial replacements (e.g., #tag before #tag/subtag)
        sorted_tags_to_replace = sorted(tags_to_replace.keys(), key=len, reverse=True)

        for old_tag in sorted_tags_to_replace:
            new_tag = tags_to_replace[old_tag]

            if old_tag == new_tag:
                continue # Skip if tag doesn't change

            # Use regex to replace the tag only when it appears as a whole word/tag entity.
            # Pattern: (?<!\S) ensures it's not preceded by a non-whitespace char (start of line/space)
            #          re.escape(old_tag) handles special characters in the tag name
            #          (?!\S) ensures it's not followed by a non-whitespace char (end of line/space/punctuation)
            pattern = r'(?<!\S)' + re.escape(old_tag) + r'(?!\S)'

            # Perform replacement using re.sub
            new_modified_content, num_replacements = re.subn(pattern, new_tag, modified_content)

            if num_replacements > 0:
                self.log_debug(f"Replaced '{old_tag}' with '{new_tag}' {num_replacements} time(s).")
                modified_content = new_modified_content
                changes_made = True

        if changes_made:
            self.log_info("Tag standardization changes applied to content.")
            return modified_content
        else:
            self.log_info("No tags needed standardization in this content.")
            return None
            
    def _get_default_system_prompt(self) -> str:
        """Returns the default system prompt for tag standardization."""
        return (
            """
            You are an expert tag standardizer. Your task is to review a list of tags from an Obsidian vault,
            identify similar tags, group them, and select a single, standardized "master tag" for each group.

            Follow these rules for the master tag:
            1. It should be one of the tags already present in the identified group, or a slight variation that is clearer.
            2. It MUST start with a single '#'.
            3. It should use lowercase letters.
            4. It should use underscores (_) instead of spaces or hyphens (-) if separating words.
            5. It should be concise and descriptive.

            You will be provided with a list of all unique tags (excluding exempt ones) in JSON format.
            Respond ONLY with a JSON object where keys are the original tags from the input list,
            and values are their chosen master tag (which MUST follow the rules above).
            Include ALL original tags from the input in your output JSON, mapping each to its chosen master tag.
            Ensure that tags you consider unique (not part of a group) are mapped to themselves after applying the formatting rules (lowercase, underscores, # prefix).
            """
        )

    def _get_default_user_prompt(self) -> str:
        """Returns the default user prompt template for tag standardization."""
        return (
            """
            Standardize the following list of tags according to the rules provided in the system prompt.
            Return a JSON object mapping every original tag to its standardized master tag.

            Example input list: ["#mentalHealth", "#Mental_health", "#therapy", "#counseling", "#unique-tag"]
            Example output format:
            {{
              "#mentalHealth": "#mental_health",
              "#Mental_health": "#mental_health",
              "#therapy": "#therapy",
              "#counseling": "#therapy",
              "#unique-tag": "#unique_tag"
            }}

            Here are the tags to process:
            {tags_json}
            """
        )