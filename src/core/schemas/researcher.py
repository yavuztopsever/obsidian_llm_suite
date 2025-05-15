from pydantic import BaseModel, Field, validator, model_validator
from typing import List, Dict, Any, Optional

from src.core.schemas.base import BaseSchema

class ResearchNote(BaseSchema):
    """Model representing a single research note with instructions."""
    id: str = Field(..., description="Unique identifier for this note")
    title: str = Field(..., description="Concise title for this note")
    instructions: str = Field(..., description="Detailed instructions for research on this topic")
    parent_id: Optional[str] = Field(None, description="The ID of the parent note (null if root)")
    level: int = Field(..., description="Hierarchy level (0 for root, 1 for children, etc.)")
    
    @validator('id')
    def id_must_be_valid(cls, v):
        if not v or not isinstance(v, str) or len(v.strip()) == 0:
            raise ValueError('id must be a non-empty string')
        return v
    
    @validator('level')
    def level_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('level must be a non-negative integer')
        return v

class ResearchStructure(BaseSchema):
    """Model representing the full research plan structure."""
    notes: List[ResearchNote] = Field(..., description="List of research notes")
    
    @model_validator(mode='after')
    def validate_structure(self) -> 'ResearchStructure':
        notes = self.notes
        if not notes:
            raise ValueError('Research structure must contain at least one note')
        
        # Check for unique IDs
        ids = [note.id for note in notes]
        if len(ids) != len(set(ids)):
            raise ValueError('All note IDs must be unique')
        
        # Validate parent_id references
        id_set = set(ids)
        for note in notes:
            if note.parent_id is not None and note.parent_id not in id_set:
                raise ValueError(f'Note with ID {note.id} references non-existent parent ID {note.parent_id}')
        
        # Validate that there's at least one root note
        root_notes = [note for note in notes if note.parent_id is None]
        if len(root_notes) == 0:
            raise ValueError('Research structure must have at least one root note (parent_id=None)')
        
        # Validate that level values match the hierarchy
        for note in notes:
            if note.parent_id is None and note.level != 0:
                raise ValueError(f'Root note {note.id} must have level=0')
            elif note.parent_id is not None:
                parent = next((p for p in notes if p.id == note.parent_id), None)
                if parent and note.level != parent.level + 1:
                    raise ValueError(f'Note {note.id} has level {note.level}, but its parent {note.parent_id} has level {parent.level}. Child level should be parent level + 1.')
        
        # Validate the hierarchy depth requirements (3-5 levels)
        if notes:
            max_level = max(note.level for note in notes)
            if max_level < 2:  # We need at least 3 levels (0, 1, 2)
                raise ValueError(f'Research structure has only {max_level + 1} levels, but at least 3 levels are required.')
            elif max_level > 4:  # We should not exceed 5 levels (0, 1, 2, 3, 4)
                raise ValueError(f'Research structure has {max_level + 1} levels, exceeding the maximum of 5 levels.')
                
        # Validate the note count requirements (10-15 notes)
        if len(notes) < 10:
            raise ValueError(f'Research structure has only {len(notes)} notes, but at least 10 notes are required.')
        elif len(notes) > 15:
            raise ValueError(f'Research structure has {len(notes)} notes, exceeding the maximum of 15 notes.')
            
        return self

class GeneratedNoteContent(BaseSchema):
    """Pydantic model for the expected JSON output from content generation."""
    content: str = Field(..., description="The generated Markdown content for the note, following the instructions.")
    concepts: List[str] = Field(default_factory=list, description="A list of key concepts (raw strings, no #) derived from the content.")
    sources: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Optional list of sources used, each with 'title' and 'url'.")