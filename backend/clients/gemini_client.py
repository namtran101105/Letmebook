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
        max_retries: int = 3,
    ):
        """
        Initialise Gemini client.

        Args:
            api_key: Gemini API key (defaults to settings.GEMINI_KEY).
            model_name: Model identifier (defaults to settings.GEMINI_MODEL).
            max_retries: Maximum retry attempts for failed requests.
        """
        # Lazy import to avoid circular dependency at module level
        from config.settings import settings

        self.api_key = api_key or settings.GEMINI_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.max_retries = max_retries

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
            },
        )

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=generation_config,
                    ),
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
                    sleep_time = 2 ** attempt  # 1s, 2s, 4s …
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

    # Context-manager support
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
