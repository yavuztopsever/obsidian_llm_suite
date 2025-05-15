import os
import glob
from typing import List

def scan_directory(path: str, extension: str = '.md') -> List[str]:
    """Scans a directory recursively for files with a specific extension.

    Args:
        path: The absolute path to the directory to scan.
        extension: The file extension to look for (including the dot, e.g., '.md').

    Returns:
        A list of absolute file paths matching the extension.
    """
    if not os.path.isdir(path):
        # Consider logging this instead of printing
        print(f"Error: Path is not a valid directory: {path}")
        return []

    if not extension.startswith('.'):
        extension = '.' + extension # Ensure the extension starts with a dot

    filepaths = []
    # Use recursive glob pattern
    pattern = os.path.join(path, '**', f'*{extension}')
    for filepath in glob.glob(pattern, recursive=True):
        if os.path.isfile(filepath): # Ensure it's a file, not a directory matching the pattern
            filepaths.append(os.path.abspath(filepath))
    return filepaths

def read_file(filepath: str) -> str:
    """Reads the content of a file.

    Args:
        filepath: The absolute path to the file.

    Returns:
        The content of the file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there's an error reading the file.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Log error
        print(f"Error: File not found at {filepath}")
        raise # Re-raise the exception for the caller to handle
    except IOError as e:
        # Log error
        print(f"Error reading file {filepath}: {e}")
        raise # Re-raise

def write_file(filepath: str, content: str):
    """Writes content to a file, creating directories if necessary.

    Args:
        filepath: The absolute path to the file.
        content: The string content to write.

    Raises:
        IOError: If there's an error writing the file.
    """
    try:
        # Ensure the directory exists
        dirpath = os.path.dirname(filepath)
        if dirpath: # Check if dirpath is not empty (e.g., for files in the root)
            os.makedirs(dirpath, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    except IOError as e:
        # Log error
        print(f"Error writing to file {filepath}: {e}")
        raise # Re-raise
