import json
from typing import Optional, Dict, Any, List, Union

from src.core.config.loader import get_config
from src.core.llm.openai_client import OpenAIClient
from src.core.llm.perplexity_client import PerplexityClient
from src.core.logging.setup import get_logger

logger = get_logger(__name__)

class LLMClient:
    """Unified interface for LLM clients."""
    
    def __init__(self, client_type: str = "openai"):
        """Initialize the appropriate LLM client.
        
        Args:
            client_type: The type of LLM client to initialize ("openai" or "perplexity").
            
        Raises:
            ValueError: If the client_type is unknown.
        """
        self.client_type = client_type
        if client_type == "openai":
            self.client = OpenAIClient()
            logger.info("Initialized OpenAI client")
        elif client_type == "perplexity":
            self.client = PerplexityClient()
            logger.info("Initialized Perplexity client")
        else:
            raise ValueError(f"Unknown client type: {client_type}")
            
    def generate_text(self, system_prompt: str, user_prompt: str, model: Optional[str] = None, 
                     temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> Optional[str]:
        """Generate text using the appropriate client.
        
        Args:
            system_prompt: The system message to guide the assistant.
            user_prompt: The user's message or prompt.
            model: The model to use. If None, uses the default from config.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional arguments to pass to the client.
            
        Returns:
            The generated text, or None if an error occurred.
        """
        if self.client_type == "openai":
            return self.client.generate_text_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        elif self.client_type == "perplexity":
            result = self.client.generate_text_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return result.get("content") if isinstance(result, dict) and "content" in result else None
            
    def generate_json(self, system_prompt: str, user_prompt: str, model: Optional[str] = None,
                     schema_class: Optional[Any] = None, json_schema: Optional[Dict[str, Any]] = None,
                     temperature: float = 0.5, max_tokens: int = 2000, **kwargs) -> Optional[Union[Dict[str, Any], Any]]:
        """Generate JSON using the appropriate client.
        
        Args:
            system_prompt: The system message, emphasizing JSON output.
            user_prompt: The user's message or prompt.
            model: The model to use. If None, uses the default from config.
            schema_class: Optional Pydantic model class for validation (used by OpenAI structured outputs).
            json_schema: Optional JSON schema for validation (used by Perplexity).
            temperature: Sampling temperature (used only if not overridden by client-specific logic like OpenAI structured outputs).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional arguments to pass to the client.
            
        Returns:
            The parsed JSON object (dict or Pydantic model), or None if an error occurred.
        """
        if self.client_type == "openai":
            # Pass schema_class to leverage OpenAI's structured outputs
            # Temperature is handled internally by generate_json_response based on mode
            result = self.client.generate_json_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema_class=schema_class, # Pass the Pydantic class
                model=model,
                max_tokens=max_tokens,
                # No temperature here - let the OpenAI client handle it
                **kwargs
            )
            # generate_json_response now returns either a validated Pydantic object or a dict/None
            return result
            
        elif self.client_type == "perplexity":
            if json_schema:
                schema_name = kwargs.pop("schema_name", "structured_output")
                schema_description = kwargs.pop("schema_description", "Generate structured output based on schema.")
                
                result = self.client.generate_json_with_schema(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    json_schema=json_schema,
                    schema_name=schema_name,
                    schema_description=schema_description,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                if "error" in result:
                    logger.error(f"Perplexity JSON generation error: {result['error']}")
                    return None
                
                data = result.get("data")
                
                if data and schema_class:
                    try:
                        return schema_class(**data)
                    except Exception as e:
                        logger.error(f"Failed to validate Perplexity JSON with schema_class: {e}")
                        return None
                
                return data
            else:
                logger.error("Perplexity requires a json_schema for JSON generation")
                return None