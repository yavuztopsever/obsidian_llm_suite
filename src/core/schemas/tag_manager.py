from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Set

from src.core.schemas.base import BaseSchema

class TagStandardizationMap(BaseSchema):
    """Schema for tag standardization mapping."""
    mapping: Dict[str, str] = Field(..., description="Mapping of original tags to standardized tags")