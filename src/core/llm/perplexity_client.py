import requests
import json
import os
import sys  # Added import sys
import re  # Added import re
from typing import Optional, Dict, Any, List  # Updated import
from requests.exceptions import RequestException, Timeout

# Import the centralized config loader
from src.core.config.loader import get_config  # Fixed import

class PerplexityClient:
    """A client for interacting with the Perplexity API using centralized configuration."""

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, api_key: Optional[str] = None):
        """Initializes the Perplexity client.

        Args:
            api_key: Optional Perplexity API key. If not provided, it's fetched
                     from the central configuration ('perplexity_api_key').
        """
        self.api_key = api_key or get_config('perplexity_api_key')
        if not self.api_key:
            # Consider raising a more specific configuration error
            raise ValueError("Perplexity API key not found in configuration.")
        # Consider adding logging here

    def _call_api(self, model: str, messages: list, temperature: float = 0.4, max_tokens: int = 4000, response_format: Optional[Dict[str, Any]] = None, timeout: Optional[int] = None, web_search_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Internal helper to make the API call and handle common errors.

        Returns:
            A dictionary containing either the parsed JSON response under 'data'
            or an error message under 'error'.
        """
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        if web_search_options:
            payload["web_search_options"] = web_search_options

        try:
            # Log the request being sent (optional)
            print(f"Sending request to Perplexity API (Model: {model}, Timeout: {timeout}s)...", file=sys.stderr)

            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=timeout)

            # Log raw response status and snippet (optional)
            print(f"API Response Status Code: {response.status_code}", file=sys.stderr)
            # print(f"API Raw Response Snippet: {response.text[:200]}...", file=sys.stderr)

            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

            api_response_data = response.json()

            # Validate response structure (basic)
            if not isinstance(api_response_data, dict) or "choices" not in api_response_data or not api_response_data["choices"]:
                return {"error": "Invalid API response structure from Perplexity.", "raw_response": api_response_data}

            message_content = api_response_data["choices"][0].get("message", {}).get("content")
            if message_content is None:
                return {"error": "Could not extract message content from Perplexity response.", "raw_response": api_response_data}

            # If expecting JSON, try parsing
            if response_format and response_format.get("type") in ["json_object", "json_schema"]:
                # Handle potential <think> block from reasoning models
                think_block_match = re.search(r"<think>.*?</think>\s*", message_content, re.DOTALL)
                json_content_to_parse = message_content
                if think_block_match:
                    # Extract content after the </think> tag
                    json_content_to_parse = message_content[think_block_match.end():].strip()
                    # Log that we stripped the think block (optional)
                    # print("Stripped <think> block before JSON parsing.", file=sys.stderr)

                if not json_content_to_parse:
                     return {"error": "No content left after potentially stripping <think> block.", "raw_content": message_content}

                try:
                    # print(f"Attempting to parse JSON: {json_content_to_parse[:100]}...", file=sys.stderr) # Debugging line
                    parsed_json = json.loads(json_content_to_parse)
                    return {"data": parsed_json}
                except json.JSONDecodeError as e:
                    # Log the content that failed parsing for easier debugging
                    error_detail = f"Failed to parse JSON content from Perplexity: {e}"
                    # print(f"Failed JSON content: {json_content_to_parse}", file=sys.stderr) # Debugging line
                    return {"error": error_detail, "raw_content": message_content} # Return original message_content for context
            else:
                # Return raw text content if not JSON format
                return {"data": message_content}

        except Timeout:
            return {"error": f"Perplexity API request timed out after {timeout} seconds."}
        except RequestException as e:
            error_message = f"Perplexity API request failed: {e}"
            if e.response is not None:
                error_message += f" - Status: {e.response.status_code} - Body: {e.response.text[:200]}..."
            return {"error": error_message}
        except Exception as e:
            return {"error": f"An unexpected error occurred during Perplexity API call: {e}"}

    def generate_json_with_schema(self, system_prompt: str, user_prompt: str, json_schema: Dict[str, Any], schema_name: str = "structured_output", schema_description: str = "Generate structured output based on schema.", model: Optional[str] = None, temperature: float = 0.4, max_tokens: int = 16000, timeout: Optional[int] = 60, web_search_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generates a response structured according to a provided JSON schema.

        Args:
            system_prompt: The system message guiding the assistant.
            user_prompt: The user's message or prompt.
            json_schema: The JSON schema definition.
            schema_name: A name for the schema (used by the API).
            schema_description: A description for the schema (used by the API).
            model: The Perplexity model to use (e.g., 'sonar-small-32k-online'). Defaults to config or a class default.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate. Increased default to 16000.
            timeout: Request timeout in seconds.
            web_search_options: Additional options for web search.

        Returns:
            A dictionary containing the parsed JSON object under 'data' or an error message under 'error'.
        """
        model = model or get_config('researcher.perplexity_model', 'llama-3-sonar-large-32k-online') # Default from config
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "description": schema_description,
                "schema": json_schema
            }
        }

        return self._call_api(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens, # Pass the potentially larger max_tokens value
            response_format=response_format,
            timeout=timeout,
            web_search_options=web_search_options
        )


    def generate_text_completion(self, system_prompt: str, user_prompt: str, model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 4000, timeout: Optional[int] = 600, web_search_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generates a text response without forcing JSON structure.

        Args:
            system_prompt: The system message guiding the assistant.
            user_prompt: The user's message or prompt.
            model: The Perplexity model to use. Defaults to config or a class default.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            timeout: Request timeout in seconds.
            web_search_options: Additional options for web search.

        Returns:
            A dictionary containing either the response under 'content' and optionally 'sources',
            or an error message under 'error'.
        """
        model = model or get_config('researcher.perplexity_model', 'llama-3-sonar-large-32k-online')  # Default from config
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self._call_api(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=None,  # No specific format, allowing free text
            timeout=timeout,
            web_search_options=web_search_options
        )

        if "error" in response:
            return response

        text_content = response.get("data")
        if text_content:
            # Extract potential sources (if model returns them)
            # This is a basic heuristic - actual extraction may depend on model/format
            sources = []
            
            # Look for a sources or references section
            sources_section_match = re.search(r'(?:##\s*Sources|##\s*References)(.*?)(?:##|$)', text_content, re.DOTALL | re.IGNORECASE)
            
            if sources_section_match:
                sources_text = sources_section_match.group(1).strip()
                # Extract links as potential sources
                links = re.findall(r'\[(.*?)\]\((https?://[^\s)]+)\)', sources_text)
                if links:
                    sources = [{"title": title, "url": url} for title, url in links]
                    # If we found formatted links, we return them separately
                    return {
                        "content": text_content,
                        "sources": sources
                    }
            
            # If no separate sources section with formatted links was found
            return {"content": text_content}

