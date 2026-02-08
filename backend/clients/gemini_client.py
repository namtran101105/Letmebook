"""
Google Gemini API client wrapper with retry logic and structured logging.

Uses the google-genai SDK (``from google import genai``).

Usage:
    from clients.gemini_client import GeminiClient

    client = GeminiClient()
    text = await client.generate_content(
        prompt="Generate a Kingston itinerary...",
        system_instruction="You are a trip planner.",
        request_id="req-123",
    )
"""

import asyncio
import logging
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class ExternalAPIError(Exception):
    """Raised when an external API call fails after retries."""

    def __init__(self, service: str, error: str, retry_count: int = 0):
        self.service = service
        self.error = error
        self.retry_count = retry_count
        super().__init__(f"{service} API failed: {error} (retries: {retry_count})")


class GeminiClient:
    """Async wrapper for Google Gemini API with retry and logging."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialise Gemini client.

        Args:
            api_key: Gemini API key (defaults to settings.GEMINI_KEY).
            model_name: Model identifier (defaults to settings.GEMINI_MODEL).
            max_retries: Maximum retry attempts for failed requests.
            timeout: Request timeout in seconds.
        """
        # Lazy import to avoid circular dependency at module level
        from config.settings import settings

        self.api_key = api_key or settings.GEMINI_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.max_retries = max_retries if max_retries is not None else settings.GEMINI_MAX_RETRIES
        self.timeout = timeout if timeout is not None else settings.GEMINI_TIMEOUT

        if not self.api_key:
            raise ValueError("Gemini API key required — set GEMINI_KEY in .env")

        # Configure the google-genai client
        self.client = genai.Client(api_key=self.api_key)

    async def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """
        Generate text content via Gemini API.

        Args:
            prompt: The user prompt text.
            system_instruction: Optional system-level instruction.
            temperature: Sampling temperature (0-2).
            max_tokens: Maximum output tokens.
            request_id: UUID for log correlation.

        Returns:
            Generated text string.

        Raises:
            ExternalAPIError: If the API call fails after all retries.
        """
        from config.settings import settings

        temp = temperature if temperature is not None else settings.GEMINI_ITINERARY_TEMPERATURE
        tokens = max_tokens or settings.GEMINI_ITINERARY_MAX_TOKENS

        generation_config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=tokens,
        )

        if system_instruction:
            generation_config.system_instruction = system_instruction

        logger.debug(
            "Calling Gemini API",
            extra={
                "request_id": request_id,
                "model": self.model_name,
                "prompt_length": len(prompt),
                "temperature": temp,
                "timeout": self.timeout,
            },
        )

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                loop = asyncio.get_event_loop()
                # Use asyncio timeout to prevent hanging
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                            config=generation_config,
                        ),
                    ),
                    timeout=self.timeout,
                )

                result_text = response.text
                logger.info(
                    "Gemini API success",
                    extra={
                        "request_id": request_id,
                        "response_length": len(result_text),
                        "model": self.model_name,
                    },
                )
                return result_text

            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError(f"Gemini API timeout after {self.timeout}s")
                logger.warning(
                    "Gemini API timeout (attempt %d/%d)",
                    attempt + 1,
                    self.max_retries,
                    extra={
                        "request_id": request_id,
                        "timeout": self.timeout,
                    },
                )
                if attempt < self.max_retries - 1:
                    sleep_time = 1  # Shorter sleep time for timeouts
                    logger.debug("Backing off for %ds", sleep_time)
                    await asyncio.sleep(sleep_time)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Gemini API error (attempt %d/%d)",
                    attempt + 1,
                    self.max_retries,
                    extra={
                        "request_id": request_id,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
                if attempt < self.max_retries - 1:
                    sleep_time = 1  # Reduced sleep time: 1s instead of exponential backoff
                    logger.debug("Backing off for %ds", sleep_time)
                    await asyncio.sleep(sleep_time)

        logger.error(
            "Gemini API failed after retries",
            extra={"request_id": request_id, "max_retries": self.max_retries},
            exc_info=True,
        )
        raise ExternalAPIError(
            service="Gemini",
            error=str(last_error),
            retry_count=self.max_retries,
        )

    def chat_with_history(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Send a full conversation history to Gemini and return the assistant reply.

        Args:
            messages: Ordered list of {"role": ..., "content": ...} dicts
                      (system / user / assistant).
            temperature: Controls randomness (0.0-2.0).
            max_tokens: Maximum tokens in the response.

        Returns:
            The assistant's reply as a plain string.
        """
        from config.settings import settings

        generation_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        # Extract system instruction if present
        system_instruction = None
        chat_messages = messages
        if messages and messages[0].get("role") == "system":
            system_instruction = messages[0]["content"]
            chat_messages = messages[1:]
            generation_config.system_instruction = system_instruction

        # Convert messages to Gemini format
        contents = []
        for msg in chat_messages:
            role = msg["role"]
            content = msg["content"]
            
            # Map OpenAI-style roles to Gemini roles
            if role == "assistant":
                role = "model"
            elif role == "system":
                continue  # Already handled above
            
            contents.append(types.Content(role=role, parts=[types.Part(text=content)]))

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=generation_config,
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API chat request failed: {str(e)}")

    # Context-manager support
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
