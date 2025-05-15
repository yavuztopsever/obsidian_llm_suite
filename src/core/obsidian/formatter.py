import re
import datetime
from typing import Dict, Any, Union, List # Removed unused imports: yaml, frontmatter, PlainScalarString

def format_obsidian_link(note_title: str) -> str:
    """Formats a note title into an Obsidian wikilink.

    Args:
        note_title: The title of the note.

    Returns:
        A string in the format [[note_title]].
    """
    # Basic cleaning: remove characters invalid in filenames/links if needed,
    # although Obsidian handles many characters in titles.
    # For simplicity, we assume the title is already valid or Obsidian handles it.
    return f"[[{note_title}]]"

def format_obsidian_tag(tag_name: str) -> str:
    """Formats a string into a valid Obsidian tag.

    Ensures the tag starts with '#', uses lowercase, and replaces spaces/hyphens with underscores.

    Args:
        tag_name: The raw tag name (can be with or without leading '#').

    Returns:
        A formatted Obsidian tag string (e.g., #my_tag).
    """
    if not tag_name:
        return "" # Return empty if input is empty
    # Remove leading/trailing whitespace
    cleaned_tag = tag_name.strip()
    # Remove leading '#' if present, for consistent processing
    if cleaned_tag.startswith('#'):
        cleaned_tag = cleaned_tag[1:]
    # Replace spaces and hyphens with underscores
    cleaned_tag = re.sub(r'[\s-]+', '_', cleaned_tag)
    # Convert to lowercase
    cleaned_tag = cleaned_tag.lower()
    # Remove any characters not allowed in tags (alphanumeric, _, /)
    cleaned_tag = re.sub(r'[^a-z0-9_/]', '', cleaned_tag)
    # Add the leading '#'
    if cleaned_tag:
        return f"#{cleaned_tag}"
    else:
        return "" # Return empty if cleaning resulted in an empty string

def format_metadata_section(note_type: str, concepts: List[str], parent_note_title: str | None, related_notes_titles: List[str] | None) -> str:
    """Formats metadata into a plain text block for Obsidian notes.

    Args:
        note_type: The type of the note (e.g., 'definition', 'concept').
        concepts: A list of concept strings.
        parent_note_title: The title of the primary parent note, if any.
        related_notes_titles: A list of titles of other related notes, if any.

    Returns:
        A formatted string containing the metadata block.
    """
    lines = []
    # Format note_type
    formatted_note_type = format_obsidian_tag(note_type) if note_type else "#note" # Default if empty
    lines.append(f"note_type: {formatted_note_type}")

    # Format concepts
    formatted_concepts = " ".join(format_obsidian_tag(c) for c in concepts if c)
    lines.append(f"concepts: {formatted_concepts if formatted_concepts else '#placeholder'}") # Default if empty

    # Format parent_note
    if parent_note_title:
        formatted_link = format_obsidian_link(parent_note_title)
        lines.append(f"parent_note: {formatted_link}") # Changed key to parent_note:

    # Format related_notes (plural)
    if related_notes_titles:
        formatted_links = ", ".join(format_obsidian_link(title) for title in related_notes_titles if title)
        if formatted_links:
            lines.append(f"related_notes: {formatted_links}")

    return "\n".join(lines)

def format_note(content: str, note_type: str, concepts: List[str], parent_note_title: str | None = None, related_notes_titles: List[str] | None = None) -> str:
    """Formats the entire note content including a plain text metadata block.

    Args:
        content (str): The main body content of the note.
        note_type (str): The type of the note.
        concepts (List[str]): A list of concept strings.
        parent_note_title (str | None): The title of the parent note, if any.
        related_notes_titles (List[str] | None): A list of titles of other related notes, if any.

    Returns:
        str: The complete formatted note content with the metadata block prepended.
    """
    metadata_block = format_metadata_section(note_type, concepts, parent_note_title, related_notes_titles)
    # Ensure there are two newlines between the metadata block and the content
    if metadata_block:
        return f"{metadata_block}\n\n{content.strip()}"
    else:
        # Should not happen with default note_type/concepts, but handle just in case
        return content.strip()

