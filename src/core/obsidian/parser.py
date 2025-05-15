import re
import frontmatter # Requires: pip install python-frontmatter PyYAML
from typing import Set, Dict, Optional, Any

def extract_tags(content: str) -> Set[str]:
    """Extracts Obsidian-style tags (#tag) from text content, including frontmatter.

    Args:
        content: The string content of the note.

    Returns:
        A set of unique tags found (including the leading '#').
    """
    tags: Set[str] = set()

    # 1. Extract tags from YAML frontmatter
    try:
        metadata, _ = frontmatter.parse(content)
        if metadata:
            # Look for 'tags', 'tag', 'concept' keys (case-insensitive check might be better)
            for key in ['tags', 'tag', 'concept']:
                tag_data = metadata.get(key)
                if isinstance(tag_data, list):
                    for item in tag_data:
                        if isinstance(item, str):
                            # Add '#' if missing, handle potential spaces/slashes
                            cleaned_tag = item.strip().replace(' ', '_')
                            if cleaned_tag and not cleaned_tag.startswith('#'):
                                tags.add(f"#{cleaned_tag}")
                            elif cleaned_tag.startswith('#'):
                                tags.add(cleaned_tag)
                elif isinstance(tag_data, str):
                    # Handle space-separated or comma-separated tags in a single string
                    potential_tags = re.split(r'[\s,]+', tag_data)
                    for item in potential_tags:
                        cleaned_tag = item.strip().replace(' ', '_')
                        if cleaned_tag and not cleaned_tag.startswith('#'):
                            tags.add(f"#{cleaned_tag}")
                        elif cleaned_tag.startswith('#'):
                            tags.add(cleaned_tag)
    except Exception as e:
        # Log this error appropriately
        print(f"Warning: Error parsing frontmatter for tag extraction: {e}")
        # Continue to extract from body even if frontmatter fails

    # 2. Extract inline tags from the body (excluding frontmatter and code blocks)
    # Simple regex: Find # followed by allowed characters (letters, numbers, _, -, /)
    # Avoid matching URLs or code blocks (basic exclusion)
    # Regex: (?<!\S) avoids matching mid-word. (?!\S) avoids matching if followed by non-space.
    # Need to refine to better exclude code blocks if necessary.
    body_content = content
    fm_match = re.match(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
    if fm_match:
        body_content = content[fm_match.end():]

    # Basic exclusion for code blocks (``` ... ```)
    body_no_code = re.sub(r'```.*?```', '', body_content, flags=re.DOTALL)

    inline_tag_matches = re.findall(r'(?<!\S)#([\w\/-]+)(?!\S)', body_no_code)
    for tag_name in inline_tag_matches:
        tags.add(f"#{tag_name}")

    return tags

def parse_frontmatter(content: str) -> Dict[str, Any]:
    """Parses YAML frontmatter from a string.

    Args:
        content: The string content which may contain frontmatter.

    Returns:
        A dictionary representing the parsed frontmatter metadata. Returns an
        empty dict if no frontmatter is found or if parsing fails.
    """
    try:
        post = frontmatter.loads(content)
        return post.metadata
    except Exception as e:
        # Log error appropriately
        print(f"Warning: Could not parse frontmatter: {e}")
        return {}

