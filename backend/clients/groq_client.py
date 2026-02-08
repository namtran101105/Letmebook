"""
Client for Groq API using OpenAI-compatible interface.
"""
import json
from typing import Dict, Any, List, Optional
from groq import Groq
from config.settings import settings


class GroqClient:
    """Client for interacting with Groq API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq client.

        Args:
            api_key: Optional API key. If not provided, uses settings.GROQ_API_KEY
        """
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL

        if not self.api_key:
            raise ValueError("Groq API key is required")

        # Initialize Groq client
        self.client = Groq(api_key=self.api_key)

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate content using Groq API.

        Args:
            prompt: The user prompt/question
            system_instruction: Optional system instruction for behavior control
            temperature: Controls randomness (0.0-2.0)
            max_tokens: Maximum tokens in response

        Returns:
            Generated text content
        """
        messages = []

        # Add system instruction if provided
        if system_instruction:
            messages.append({
                "role": "system",
                "content": system_instruction
            })

        # Add user prompt
        messages.append({
            "role": "user",
            "content": prompt
        })

        try:
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"Groq API request failed: {str(e)}")

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response using Groq API.

        Args:
            prompt: The user prompt/question
            system_instruction: Optional system instruction
            temperature: Controls randomness (lower for more consistent JSON)
            max_tokens: Maximum tokens in response

        Returns:
            Parsed JSON response as dictionary
        """
        messages = []

        # Build system instruction with JSON requirement
        json_system = "You must respond with valid JSON only. Do not include any explanatory text, markdown formatting, or code blocks. Return only the raw JSON object."
        if system_instruction:
            full_system = f"{system_instruction}\n\n{json_system}"
        else:
            full_system = json_system

        messages.append({
            "role": "system",
            "content": full_system
        })

        messages.append({
            "role": "user",
            "content": prompt
        })

        try:
            # Call Groq API with JSON mode
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}  # Force JSON output
            )

            content = response.choices[0].message.content

            # Parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                # Try to extract JSON from markdown code blocks if present
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                    return json.loads(json_str)
                else:
                    raise Exception(f"Failed to parse JSON response: {str(e)}\nResponse: {content}")

        except Exception as e:
            raise Exception(f"Groq API request failed: {str(e)}")

    def chat_with_history(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Send a full conversation history to Groq and return the assistant reply.

        Unlike ``generate_content`` (which accepts a single prompt string),
        this method takes the raw ``messages`` list so multi-turn context is
        preserved across calls.

        Args:
            messages: Ordered list of ``{"role": ..., "content": ...}`` dicts
                      (system / user / assistant).
            temperature: Controls randomness (0.0-2.0).
            max_tokens: Maximum tokens in the response.

        Returns:
            The assistant's reply as a plain string.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Groq API chat request failed: {str(e)}")
