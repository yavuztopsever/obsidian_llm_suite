import re

def sanitize_filename(text: str) -> str:
    """Removes or replaces characters unsuitable for filenames.

    - Removes characters: \ / * ? : " < > |
    - Replaces spaces with underscores.
    - Limits length to 100 characters.

    Args:
        text: The input string.

    Returns:
        A sanitized string suitable for use as a filename.
    """
    if not isinstance(text, str):
        text = str(text) # Attempt to convert non-strings

    # Remove invalid characters
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    # Replace spaces with underscores
    text = text.replace(" ", "_")
    # Limit length
    return text[:100]

# Add other general-purpose text manipulation functions here as needed.
# For example:
# def truncate_text(text: str, max_length: int) -> str:
#     """Truncates text to a maximum length, adding ellipsis if truncated."""
#     if len(text) > max_length:
#         return text[:max_length-3] + "..."
#     return text
