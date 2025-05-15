from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from src.core.schemas.base import BaseSchema

class EnrichmentOutput(BaseSchema):
    """Schema for enrichment output."""
    enriched_content: str = Field(..., description="The enriched content")
    concepts: List[str] = Field(default_factory=list, description="List of concepts")