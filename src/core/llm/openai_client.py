import openai
import json
from typing import Optional, Dict, Any, Type, Union
from pydantic import BaseModel

# Import the centralized config loader
from src.core.config.loader import get_config  # Fixed import

class OpenAIClient:
    """A client for interacting with the OpenAI API using centralized configuration."""

    def __init__(self, api_key: Optional[str] = None):
        """Initializes the OpenAI client.

        Args:
            api_key: Optional OpenAI API key. If not provided, it's fetched
                     from the central configuration ('openai_api_key').
        """
        self.api_key = api_key or get_config('openai_api_key')
        if not self.api_key:
            # Consider raising a more specific configuration error
            raise ValueError("OpenAI API key not found in configuration.")
        self.client = openai.OpenAI(api_key=self.api_key)
        # Consider adding logging here

    def _call_api(self, model: str, messages: list, temperature: float = 0.7, max_tokens: int = 1500, response_format: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Internal helper to make the API call and handle common errors."""
        try:
            completion_params = {
                "model": model,
                "messages": messages,
                "max_completion_tokens": max_tokens  # Using max_completion_tokens for all models
            }
            
            if response_format:
                completion_params["response_format"] = response_format
                # Do NOT add temperature if response_format is set, use API default (1.0)
            else:
                # Only add temperature if NOT using a specific response_format
                completion_params["temperature"] = temperature

            response = self.client.chat.completions.create(**completion_params)

            # Basic validation of response structure
            if response.choices and response.choices[0].message:
                message = response.choices[0].message
                
                # Check for content field first
                if message.content:
                    return message.content
                
                # If content is None, check for refusal field which may contain our data
                elif hasattr(message, 'refusal') and message.refusal:
                    # The 'refusal' field sometimes contains the actual JSON response
                    if response_format and response_format.get("type") == "json_object":
                        # Extract JSON content if it starts with indicators like 'json' or '['
                        refusal_content = message.refusal
                        if refusal_content.startswith(('json', '[')):
                            # If it starts with 'json', strip that prefix
                            if refusal_content.startswith('json'):
                                refusal_content = refusal_content[4:].strip()
                            return refusal_content
                    
                    # Return refusal content as-is if we're not expecting JSON
                    return message.refusal
                
            # If we reach here, there's a problem with the response structure
            print(f"Error: Unexpected OpenAI response structure: {response}")
            return None

        except openai.AuthenticationError:
            # Log error: Authentication failed
            print("Error: OpenAI authentication failed. Check your API key.")
            # Potentially raise a custom exception
            return None
        except openai.APIError as e:
            # Log error: General API error
            print(f"OpenAI API error occurred: {e}")
            # Potentially raise a custom exception
            return None
        except Exception as e:
            # Log error: Unexpected error
            print(f"An unexpected error occurred during OpenAI API call: {e}")
            # Potentially raise a custom exception
            return None

    def generate_text_completion(self, system_prompt: str, user_prompt: str, model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1500) -> Optional[str]:
        """Generates a text completion using the chat API.

        Args:
            system_prompt: The system message to guide the assistant.
            user_prompt: The user's message or prompt.
            model: The OpenAI model to use (e.g., 'gpt-4o'). Defaults to config or a class default.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            The generated text content as a string, or None if an error occurred.
        """
        model = model or get_config('default_llm_model', 'gpt-4o-mini') # Use default from config or fallback
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self._call_api(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)

    def generate_json_response(self, system_prompt: str, user_prompt: str, schema_class: Optional[Type[BaseModel]] = None, model: Optional[str] = None, max_tokens: int = 4000) -> Optional[Union[Dict[str, Any], BaseModel]]:
        """Generates a response expected to be a JSON object, optionally conforming to a Pydantic schema.

        Args:
            system_prompt: The system message, emphasizing JSON output.
            user_prompt: The user's message or prompt.
            schema_class: Optional Pydantic model class to enforce output structure.
            model: The OpenAI model to use. Defaults to config or a class default.
            max_tokens: Maximum tokens to generate.

        Returns:
            The parsed JSON object as a dictionary or Pydantic model instance, or None if an error occurred.
        """
        model = model or get_config('default_llm_model', 'gpt-4o-mini') # Ensure model supports JSON mode / structured outputs
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response_format_param = None
        # Use Structured Outputs if a Pydantic schema is provided
        if schema_class:
            try:
                json_schema_dict = schema_class.model_json_schema()
                # Add the required 'name' field and nest the schema under 'schema'
                schema_name = schema_class.__name__ # Use Pydantic model name as schema name
                response_format_param = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "description": f"JSON schema for {schema_name}", # Optional but good practice
                        "schema": json_schema_dict # Nest the actual schema here
                    }
                }
                # Note: Temperature might need to be default (1.0) for some models with json_schema
                # We are removing the temperature parameter from this method's signature
                # and relying on the API default when response_format is used.
            except Exception as e:
                print(f"Error generating JSON schema from Pydantic model: {e}")
                return None # Cannot proceed without a valid schema for structured output
        else:
             # Fallback to basic JSON mode if no schema is given
             # IMPORTANT: Prompt must explicitly ask for JSON in this case.
             response_format_param = {"type": "json_object"}

        # Make the API call (temperature is omitted here to use API default when response_format is set)
        json_string = self._call_api(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            response_format=response_format_param
            # temperature is intentionally omitted here
        )

        if json_string:
            try:
                # Check for refusal first (needs adjustment in _call_api or here)
                # Assuming _call_api returns the raw string for now
                # A proper implementation should handle the refusal structure shown in docs
                if "refusal" in json_string: # Basic check, might need refinement
                     print(f"OpenAI Refusal: {json_string}")
                     return None

                parsed_data = json.loads(json_string)
                
                # If a schema class was provided, validate and return Pydantic object
                if schema_class:
                    try:
                        return schema_class(**parsed_data)
                    except Exception as pydantic_error:
                        print(f"Error validating response against Pydantic schema: {pydantic_error}")
                        print(f"Raw response data: {parsed_data}")
                        return None # Validation failed
                else:
                    # Return raw dictionary if no schema class was used
                    return parsed_data
            except json.JSONDecodeError as e:
                print(f"Error: Failed to decode JSON response from OpenAI: {e}")
                print(f"Raw response string: {json_string}")
                return None
        return None

