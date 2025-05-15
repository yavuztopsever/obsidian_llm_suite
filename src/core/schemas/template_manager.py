from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from src.core.schemas.base import BaseSchema

class TemplateOutput(BaseSchema):
    """Schema for template processing output."""
    title: str = Field(..., description="The main title for the note.")
    creation_date: str = Field(..., description="Creation date in ISO 8601 format (YYYY-MM-DD).")
    note_type: str = Field("note", description="The primary type/category of the note.")
    concepts: List[str] = Field(default_factory=list, description="List of key concepts or keywords (raw strings, no #).")
    related_notes: List[str] = Field(default_factory=list, description="List of titles of related notes (raw titles, no [[ ]]).")
    summary: str = Field(..., description="A brief summary of the note content.")
    content: str = Field(..., description="The main body content, potentially restructured or enhanced, in Markdown format.")