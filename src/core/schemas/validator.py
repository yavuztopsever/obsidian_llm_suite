import json
from typing import Dict, Any, Type, Optional, Union
from jsonschema import validate, ValidationError
from pydantic import BaseModel

from src.core.logging.setup import get_logger

logger = get_logger(__name__)

class SchemaValidator:
    """Handles validation of data against schemas."""
    
    def validate_with_pydantic(self, data: Dict[str, Any], model_class: Type[BaseModel]) -> Optional[BaseModel]:
        """Validate data using a Pydantic model.
        
        Args:
            data: The data to validate.
            model_class: The Pydantic model class to validate against.
            
        Returns:
            The validated model instance, or None if validation failed.
        """
        try:
            validated_data = model_class(**data)
            logger.debug(f"Successfully validated data with {model_class.__name__}")
            return validated_data
        except Exception as e:
            logger.error(f"Pydantic validation failed: {e}")
            return None
    
    def validate_with_jsonschema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate data using JSON Schema.
        
        Args:
            data: The data to validate.
            schema: The JSON schema to validate against.
            
        Returns:
            True if validation succeeded, False otherwise.
        """
        try:
            validate(instance=data, schema=schema)
            logger.debug("Successfully validated data with JSON Schema")
            return True
        except ValidationError as e:
            logger.error(f"JSON Schema validation failed: {e.message}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during JSON Schema validation: {e}")
            return False
    
    def clean_data(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Clean data based on a schema.
        
        This method removes any fields not defined in the schema and applies
        default values for missing fields.
        
        Args:
            data: The data to clean.
            schema: The schema defining the expected structure.
            
        Returns:
            The cleaned data.
        """
        cleaned_data = {}
        
        # Only process if schema has properties
        if not isinstance(schema, dict) or "properties" not in schema:
            logger.warning("Schema does not have properties, returning data as-is")
            return data
        
        properties = schema.get("properties", {})
        
        # Apply defined properties
        for key, prop_schema in properties.items():
            # If key exists in data, use it (after cleaning if it's an object)
            if key in data:
                value = data[key]
                
                # If value is an object and property schema defines nested properties
                if isinstance(value, dict) and isinstance(prop_schema, dict) and "properties" in prop_schema:
                    cleaned_data[key] = self.clean_data(value, prop_schema)
                else:
                    cleaned_data[key] = value
            # Otherwise, use default if defined
            elif "default" in prop_schema:
                cleaned_data[key] = prop_schema["default"]
        
        return cleaned_data