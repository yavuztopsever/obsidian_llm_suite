from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class BaseSchema(BaseModel):
    """Base class for all schemas."""
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Forbid extra attributes

class ObsidianNote(BaseSchema):
    """Schema for an Obsidian note."""
    title: str = Field(..., description="The title of the note")
    content: str = Field(..., description="The content of the note")
    note_type: str = Field("note", description="The type of the note")
    concepts: List[str] = Field(default_factory=list, description="List of concepts")
    parent_note_title: Optional[str] = Field(None, description="The title of the parent note")