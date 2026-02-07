# Clients Module - Agent Instructions

**Parent Contexts**:
- `MONVOYAGE/CLAUDE.md` (project-wide architecture, testing conventions)
- `MONVOYAGE/backend/CLAUDE_EMBEDDED.md` (backend-operational rules, MVP requirements)

**Module Purpose**: External API client wrappers for Gemini (primary), Groq (fallback), Google Maps, Weather API, and other third-party services. Handles authentication, retries, rate limiting, and error handling.

---

## Module Responsibilities

### Current (Phase 1)
1. **Gemini Client** (`gemini_client.py`) - Primary LLM wrapper using `google-genai` SDK for NLP extraction and itinerary generation
2. **Groq Client** (`groq_client.py`) - Fallback LLM wrapper for Groq API (used when Gemini unavailable)
3. HTTP client configuration (timeouts, retries, headers)
4. API authentication and key management
5. Response parsing and error handling

### Planned (Phase 2/3)
6. **Google Maps Client** (`google_maps_client.py`) - Geocoding, directions, distance matrix
7. **Weather Client** (`weather_client.py`) - Weather forecasts and historical data
8. **MongoDB Client** (`mongodb_client.py`) - Database connection and operations
9. Rate limiting and request throttling
10. Response caching for repeated requests

---

## Files in This Module

### `gemini_client.py` (Phase 1 - Primary LLM)

**Purpose**: Wrapper for Google Gemini API using the `google-genai` SDK (`from google import genai`). This is the primary LLM client for all extraction and itinerary generation.

**Must Include**:
```python
import logging
from typing import Optional
from google import genai
from backend.config.settings import settings

class GeminiClient:
    """Client wrapper for Google Gemini API (primary LLM)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize Gemini client.

        Args:
            api_key: Gemini API key (defaults to settings.GEMINI_KEY)
            model: Model name (defaults to settings.GEMINI_MODEL)
        """
        self.api_key = api_key or settings.GEMINI_KEY
        self.model = model or settings.GEMINI_MODEL
        self.logger = logging.getLogger(__name__)

        if not self.api_key:
            raise ValueError("Gemini API key required (set GEMINI_KEY env var)")

        # Initialize the google-genai client
        self.client = genai.Client(api_key=self.api_key)

    async def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        request_id: Optional[str] = None
    ) -> str:
        """
        Generate content using Gemini API.

        Args:
            prompt: The user prompt to send
            system_instruction: System instruction for the model
            temperature: Sampling temperature 0-1 (defaults to settings value)
            max_tokens: Max tokens in response (defaults to settings value)
            request_id: UUID for correlation logging

        Returns:
            Generated text content as string

        Raises:
            ExternalAPIError: If API call fails after retries
        """
        self.logger.debug("Calling Gemini API", extra={
            "request_id": request_id,
            "model": self.model,
            "prompt_length": len(prompt),
            "temperature": temperature
        })

        try:
            config = genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_instruction
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )

            result_text = response.text

            self.logger.info("Gemini API success", extra={
                "request_id": request_id,
                "model": self.model,
                "response_length": len(result_text)
            })

            return result_text

        except Exception as e:
            self.logger.error("Gemini API failed", extra={
                "request_id": request_id,
                "error_type": type(e).__name__,
                "error": str(e)
            }, exc_info=True)

            raise ExternalAPIError(
                service="Gemini",
                error=str(e)
            )
```

**Key Design Decisions**:
- Uses `from google import genai` (google-genai SDK), NOT the older `google.generativeai` package
- Does NOT use httpx directly; relies on the SDK's built-in HTTP handling
- Returns plain string (not structured response object)
- All config comes from `settings.py` (no separate `gemini.py` config file)

---

### `groq_client.py` (Phase 1 - Fallback LLM)

**Purpose**: Wrapper for Groq API with retry logic, error handling, and logging. Used as fallback when Gemini is unavailable.

**Must Include**:
```python
import httpx
import logging
from typing import Dict, Any, List, Optional
from backend.config.settings import settings

class GroqClient:
    """Client wrapper for Groq LLM API (fallback)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize Groq client.

        Args:
            api_key: Groq API key (defaults to settings.GROQ_API_KEY)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.api_key = api_key or settings.GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1"
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)

        if not self.api_key:
            raise ValueError("Groq API key required")

        # HTTP client with retry configuration
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call Groq chat completion API.

        Args:
            messages: List of chat messages [{"role": "user", "content": "..."}]
            model: Model name (defaults to settings.GROQ_MODEL)
            temperature: Sampling temperature 0-1 (defaults to settings.GROQ_TEMPERATURE)
            max_tokens: Max tokens in response (defaults to settings.GROQ_MAX_TOKENS)
            response_format: {"type": "json_object"} for JSON mode
            request_id: UUID for correlation logging

        Returns:
            API response dict with choices, usage, etc.

        Raises:
            ExternalAPIError: If API call fails after retries
        """
        payload = {
            "model": model or settings.GROQ_MODEL,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.GROQ_TEMPERATURE,
            "max_tokens": max_tokens or settings.GROQ_MAX_TOKENS
        }

        if response_format:
            payload["response_format"] = response_format

        self.logger.debug("Calling Groq API (fallback)", extra={
            "request_id": request_id,
            "model": payload["model"],
            "message_count": len(messages),
            "temperature": payload["temperature"]
        })

        # Retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    "/chat/completions",
                    json=payload
                )
                response.raise_for_status()

                result = response.json()

                self.logger.info("Groq API success (fallback)", extra={
                    "request_id": request_id,
                    "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                    "model": result.get("model")
                })

                return result

            except httpx.HTTPStatusError as e:
                last_error = e
                self.logger.warning(f"Groq API HTTP error (attempt {attempt+1}/{self.max_retries})", extra={
                    "request_id": request_id,
                    "status_code": e.response.status_code,
                    "error": str(e)
                })

                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    break

                if attempt < self.max_retries - 1:
                    await self._backoff_sleep(attempt)

            except httpx.RequestError as e:
                last_error = e
                self.logger.warning(f"Groq API request error (attempt {attempt+1}/{self.max_retries})", extra={
                    "request_id": request_id,
                    "error": str(e)
                })

                if attempt < self.max_retries - 1:
                    await self._backoff_sleep(attempt)

        # All retries failed
        self.logger.error("Groq API failed after retries (fallback)", extra={
            "request_id": request_id,
            "max_retries": self.max_retries
        }, exc_info=True)

        raise ExternalAPIError(
            service="Groq",
            error=str(last_error),
            retry_count=self.max_retries
        )

    async def _backoff_sleep(self, attempt: int):
        """Exponential backoff sleep"""
        import asyncio
        sleep_time = 2 ** attempt  # 1s, 2s, 4s, 8s...
        self.logger.debug(f"Backing off for {sleep_time}s")
        await asyncio.sleep(sleep_time)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


class ExternalAPIError(Exception):
    """Raised when external API call fails"""
    def __init__(self, service: str, error: str, retry_count: int = 0):
        self.service = service
        self.error = error
        self.retry_count = retry_count
        super().__init__(f"{service} API failed: {error} (retries: {retry_count})")
```

---

### `google_maps_client.py` (Phase 2 - Planned)

**Purpose**: Google Maps API client for geocoding and routing.

**Key Operations**:
```python
class GoogleMapsClient:
    async def geocode(self, address: str) -> Dict[str, Any]:
        """Convert address to coordinates"""
        pass

    async def distance_matrix(
        self,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving"
    ) -> Dict[str, Any]:
        """Calculate travel times between locations"""
        pass

    async def directions(
        self,
        origin: str,
        destination: str,
        mode: str = "driving"
    ) -> Dict[str, Any]:
        """Get turn-by-turn directions"""
        pass
```

---

### `weather_client.py` (Phase 2 - Planned)

**Purpose**: Weather API client for forecasts.

**Key Operations**:
```python
class WeatherClient:
    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get weather forecast"""
        pass

    async def check_outdoor_safety(
        self,
        forecast: Dict[str, Any]
    ) -> bool:
        """Check if outdoor activities are safe"""
        pass
```

---

## Non-Negotiable Rules

### LLM Client Priority
1. **Gemini is PRIMARY** - Always try Gemini first
2. **Groq is FALLBACK** - Only use if Gemini fails or is unavailable
3. **Log which client** was used for each request

### Retry Logic (All Clients)
1. **Retry 5xx errors** (server errors) up to 3 times
2. **DO NOT retry 4xx errors** (client errors - bad request, auth failure)
3. **Use exponential backoff**: 1s, 2s, 4s, 8s...
4. **Log each retry attempt** at WARNING level
5. **Raise ExternalAPIError** after max retries

### Authentication
1. **API keys from settings** (never hardcoded)
2. **Gemini uses `google-genai` SDK** authentication (API key passed to client constructor)
3. **Groq uses Authorization header** (Bearer token pattern)
4. **Redact keys in logs** (show only last 4 characters)
5. **Rotate keys** if exposed

### Timeout Handling
1. **Default timeout: 30 seconds** for LLM APIs
2. **Shorter timeout: 10 seconds** for Maps/Weather APIs
3. **Configurable** via settings
4. **Log timeout warnings** (may indicate API issues)

### Rate Limiting
1. **Respect API rate limits** (check response headers)
2. **Implement backoff** on 429 (Too Many Requests)
3. **Cache responses** when appropriate
4. **Log rate limit warnings**

---

## Logging Requirements

### What to Log
- **INFO**: API call success, tokens used, response time
- **DEBUG**: Request payload (redacted), response preview
- **WARNING**: Retry attempts, rate limits, slow responses, fallback to Groq
- **ERROR**: API failures, authentication errors, timeout errors

### Log Examples
```python
# Gemini API call start
logger.debug("Calling Gemini API", extra={
    "request_id": request_id,
    "model": "gemini-2.0-flash",
    "prompt_length": 500,
    "api_key": redact_api_key(api_key)
})

# Gemini API success
logger.info("Gemini API success", extra={
    "request_id": request_id,
    "response_length": 1200,
    "model": "gemini-2.0-flash"
})

# Fallback to Groq
logger.warning("Gemini failed, falling back to Groq", extra={
    "request_id": request_id,
    "gemini_error": "Connection timeout",
    "fallback": "Groq"
})

# Groq fallback success
logger.info("Groq API success (fallback)", extra={
    "request_id": request_id,
    "tokens_used": 245,
    "model": "llama-3.3-70b-versatile"
})

# Final failure
logger.error("All LLM clients failed", extra={
    "request_id": request_id,
    "gemini_error": "Connection timeout",
    "groq_error": "Rate limited"
}, exc_info=True)
```

### Redaction
```python
def redact_api_key(key: str) -> str:
    """Redact API key to show only last 4 chars"""
    if not key or len(key) < 8:
        return "***INVALID***"
    return f"***...{key[-4:]}"
```

---

## Testing Strategy

### Unit Tests Required (Minimum 15)

**GeminiClient Tests**:
1. Test Gemini client initialization with API key
2. Test successful content generation
3. Test content generation with system instruction
4. Test content generation with custom temperature
5. Test content generation with custom max_tokens
6. Test API key from settings default
7. Test missing API key raises ValueError
8. Test error handling on API failure

**GroqClient Tests**:
9. Test Groq client initialization
10. Test successful chat completion
11. Test JSON mode response parsing
12. Test timeout configuration
13. Test request header construction
14. Test error response parsing
15. Test async context manager (enter/exit)

### Integration Tests Required (Minimum 5)
1. Test with real Gemini API (successful call)
2. Test with real Groq API (successful call)
3. Test with invalid API key (401 error)
4. Test with network timeout
5. Test fallback from Gemini to Groq

### Negative Tests Required (Minimum 5)
1. Test GeminiClient with missing API key (must raise ValueError)
2. Test GroqClient with 4xx error (no retry)
3. Test GroqClient with 5xx error (retry then fail)
4. Test with max retries exceeded
5. Test with malformed response

### Test Examples
```python
@pytest.mark.asyncio
async def test_gemini_client_success():
    """Test successful Gemini API call"""
    client = GeminiClient(api_key="test_key")

    # Mock the google-genai response
    with mock.patch.object(client.client.models, 'generate_content') as mock_gen:
        mock_gen.return_value = MockGeminiResponse(text="Test response")

        result = await client.generate_content(
            prompt="Test prompt",
            system_instruction="Be helpful",
            temperature=0.2,
            max_tokens=2048,
            request_id="req-123"
        )

    assert result == "Test response"

@pytest.mark.asyncio
async def test_gemini_client_missing_key():
    """Test that missing API key raises ValueError"""
    with mock.patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Gemini API key required"):
            GeminiClient(api_key="")

@pytest.mark.asyncio
async def test_groq_client_success(mock_httpx):
    """Test successful Groq API call (fallback)"""
    mock_httpx.post.return_value = MockResponse(
        status_code=200,
        json_data={
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"total_tokens": 100},
            "model": "llama-3.3-70b-versatile"
        }
    )

    async with GroqClient(api_key="test_key") as client:
        result = await client.chat_completion(
            messages=[{"role": "user", "content": "Test"}],
            request_id="req-123"
        )

    assert result["choices"][0]["message"]["content"] == "Test response"
    assert result["usage"]["total_tokens"] == 100

@pytest.mark.asyncio
async def test_groq_client_retry_on_5xx(mock_httpx):
    """Test retry logic on server error"""
    mock_httpx.post.side_effect = [
        MockResponse(status_code=500),
        MockResponse(status_code=500),
        MockResponse(status_code=200, json_data={"choices": [{"message": {"content": "Success"}}]})
    ]

    async with GroqClient(api_key="test_key", max_retries=3) as client:
        result = await client.chat_completion(
            messages=[{"role": "user", "content": "Test"}],
            request_id="req-123"
        )

    assert result["choices"][0]["message"]["content"] == "Success"
    assert mock_httpx.post.call_count == 3

@pytest.mark.asyncio
async def test_groq_client_no_retry_on_4xx(mock_httpx):
    """Test no retry on client error"""
    mock_httpx.post.return_value = MockResponse(status_code=401)

    async with GroqClient(api_key="invalid_key") as client:
        with pytest.raises(ExternalAPIError) as exc_info:
            await client.chat_completion(
                messages=[{"role": "user", "content": "Test"}],
                request_id="req-123"
            )

    # Should fail immediately without retries
    assert mock_httpx.post.call_count == 1
```

---

## Error Handling

### HTTP Status Codes

**2xx Success**:
- 200 OK - Process response normally

**4xx Client Errors (DO NOT RETRY)**:
- 400 Bad Request - Invalid payload
- 401 Unauthorized - Invalid API key
- 403 Forbidden - Access denied
- 429 Too Many Requests - Rate limited (wait and retry once)

**5xx Server Errors (RETRY)**:
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable
- 504 Gateway Timeout

### Exception Hierarchy
```python
class ExternalAPIError(Exception):
    """Base exception for external API failures"""
    pass

class GeminiAPIError(ExternalAPIError):
    """Gemini-specific API error"""
    pass

class GroqAPIError(ExternalAPIError):
    """Groq-specific API error"""
    pass

class GoogleMapsAPIError(ExternalAPIError):
    """Google Maps-specific API error"""
    pass

class WeatherAPIError(ExternalAPIError):
    """Weather API-specific error"""
    pass
```

---

## Integration Points

### Used By
- `services/nlp_extraction_service.py` - Uses GeminiClient (primary) and GroqClient (fallback)
- `services/itinerary_service.py` - Uses GeminiClient for itinerary generation
- `services/weather_service.py` - Uses WeatherClient (Phase 2)

### Uses
- `config/settings.py` - API keys and configuration (all LLM config is in settings.py)
- `google-genai` - Google Gemini SDK (`from google import genai`)
- `httpx` - Async HTTP client library (for Groq)

---

## Assumptions
1. API keys are valid and active
2. External APIs return appropriate responses
3. Network connectivity is available
4. Rate limits are reasonable for MVP usage
5. Gemini is the primary LLM; Groq is optional fallback

## Open Questions
1. Should we implement client-side rate limiting?
2. Do we need response caching? If so, for how long?
3. Should we use connection pooling for HTTP clients?
4. What is acceptable API response time (SLA)?

---

**Last Updated**: 2026-02-07
**Status**: Phase 1 - GeminiClient (primary) and GroqClient (fallback) implemented
