import os
from typing import Optional
import logging
import traceback # Import traceback

# Attempt to import pypdf, handle if not installed
try:
    import pypdf
    from pypdf.errors import PdfReadError # Import specific error
except ImportError:
    pypdf = None
    PdfReadError = None # Define as None if pypdf not installed

logger = logging.getLogger(__name__)

def parse_document(file_path: str) -> Optional[str]:
    """Parses the content of a document (txt, md, pdf) into plain text.

    Args:
        file_path: The absolute path to the document file.

    Returns:
        The extracted text content as a string, or None if parsing fails or the
        file type is unsupported.
    """
    if not os.path.exists(file_path):
        logger.error(f"Document not found: {file_path}")
        return None

    _, extension = os.path.splitext(file_path.lower())

    try:
        if extension in ['.txt', '.md']:
            # Try reading with utf-8, fallback to latin-1 for robustness
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                logger.warning(f"UTF-8 decoding failed for {file_path}. Trying latin-1.")
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
        elif extension == '.pdf':
            if pypdf is None:
                logger.error("PDF parsing requires 'pypdf'. Please install it: pip install pypdf")
                return None
            
            text_content = ""
            try:
                with open(file_path, 'rb') as f:
                    reader = pypdf.PdfReader(f)
                    
                    # Check if PDF is encrypted
                    if reader.is_encrypted:
                        logger.warning(f"Skipping encrypted PDF (password protected): {file_path}")
                        return None # Cannot parse encrypted PDFs without password
                        
                    num_pages = len(reader.pages)
                    logger.info(f"Parsing PDF: {file_path} ({num_pages} pages)")
                    for page_num in range(num_pages):
                        try:
                            page = reader.pages[page_num]
                            extracted = page.extract_text()
                            if extracted:
                                text_content += extracted + "\n" # Add newline between pages
                        except Exception as page_error: # Catch errors during page extraction
                            logger.warning(f"Error extracting text from page {page_num + 1} in {file_path}: {page_error}")
                            continue # Skip problematic pages
                return text_content.strip() if text_content else None
            except PdfReadError as pdf_err:
                logger.error(f"Failed to read PDF file (possibly corrupted or invalid format) {file_path}: {pdf_err}")
                return None
            except Exception as pdf_open_err:
                 logger.error(f"Error opening or processing PDF {file_path}: {pdf_open_err}")
                 logger.debug(traceback.format_exc()) # Log full traceback for PDF errors
                 return None
        else:
            logger.warning(f"Unsupported file type '{extension}' for parsing: {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error parsing document {file_path}: {e}")
        logger.debug(traceback.format_exc()) # Log full traceback for general errors
        return None

