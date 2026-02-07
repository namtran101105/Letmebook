# Clients Module - Agent Instructions

**Parent Contexts**:
- `MONVOYAGE/CLAUDE.md` (project-wide architecture, testing conventions)
- `MONVOYAGE/backend/CLAUDE_EMBEDDED.md` (backend-operational rules, MVP requirements)

**Module Purpose**: External API client wrappers for Groq, Google Maps, Weather API, and other third-party services. Handles authentication, retries, rate limiting, and error handling.

---

## Module Responsibilities

### Current (Phase 1)
1. **Groq Client** (`groq_client.py`) - Wrapper for Groq LLM API (NLP extraction, itinerary generation)
2. HTTP client configuration (timeouts, retries, headers)
3. API authentication and key management
4. Response parsing and error handling

### Planned (Phase 2/3)
5. **Google Maps Client** (`google_maps_client.py`) - Geocoding, directions, distance matrix
6. **Weather Client** (`weather_client.py`) - Weather forecasts and historical data
7. **MongoDB Client** (`mongodb_client.py`) - Database connection and operations
8. Rate limiting and request throttling
9. Response caching for repeated requests

---

## Files in This Module

### `groq_client.py` (Phase 1 - Current)

**Purpose**: Wrapper for Groq API with retry logic, error handling, and logging.

**Must Include**:
```python
import httpx
import logging
from typing import Dict, Any, List, Optional
from backend.config.settings import settings

class GroqClient:
    """Client wrapper for Groq LLM API"""
    
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
        
        self.logger.debug("Calling Groq API", extra={
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
                
                self.logger.info("Groq API success", extra={
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
        self.logger.error("Groq API failed after retries", extra={
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

### `gemini_client.py` (Phase 1 - Alternative/Fallback)

**Purpose**: Google Gemini API client (backup for Groq).

**When to Use**: If Groq API unavailable or rate-limited.

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

### Retry Logic (All Clients)
1. **Retry 5xx errors** (server errors) up to 3 times
2. **DO NOT retry 4xx errors** (client errors - bad request, auth failure)
3. **Use exponential backoff**: 1s, 2s, 4s, 8s...
4. **Log each retry attempt** at WARNING level
5. **Raise ExternalAPIError** after max retries

### Authentication
1. **API keys from settings** (never hardcoded)
2. **Use Authorization header** (Bearer token pattern)
3. **Redact keys in logs** (show only last 4 characters)
4. **Rotate keys** if exposed

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
- **WARNING**: Retry attempts, rate limits, slow responses
- **ERROR**: API failures, authentication errors, timeout errors

### Log Examples
```python
# API call start
logger.debug("Calling Groq API", extra={
    "request_id": request_id,
    "model": "llama-3.3-70b-versatile",
    "message_count": 2,
    "api_key": redact_api_key(api_key)
})

# API success
logger.info("Groq API success", extra={
    "request_id": request_id,
    "tokens_used": 245,
    "response_time_ms": 1250
})

# Retry warning
logger.warning("API call failed, retrying", extra={
    "request_id": request_id,
    "attempt": 2,
    "max_retries": 3,
    "error": "Connection timeout"
})

# Final failure
logger.error("API call failed after retries", extra={
    "request_id": request_id,
    "service": "Groq",
    "retry_count": 3
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

### Unit Tests Required (Minimum 10)
1. Test Groq client initialization
2. Test successful chat completion
3. Test JSON mode response parsing
4. Test API key from settings
5. Test custom API key override
6. Test timeout configuration
7. Test request header construction
8. Test error response parsing
9. Test API key redaction in logs
10. Test async context manager (enter/exit)

### Integration Tests Required (Minimum 5)
1. Test with real Groq API (successful call)
2. Test with invalid API key (401 error)
3. Test with network timeout
4. Test with rate limiting (429 error)
5. Test retry logic with mock failures

### Negative Tests Required (Minimum 5)
1. Test with missing API key (must raise ValueError)
2. Test with 4xx error (no retry)
3. Test with 5xx error (retry then fail)
4. Test with max retries exceeded
5. Test with malformed response JSON

### Test Examples
```python
@pytest.mark.asyncio
async def test_groq_client_success(mock_httpx):
    """Test successful Groq API call"""
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
    # First two attempts fail with 500, third succeeds
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
    assert exc_info.value.retry_count == 0
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
- `services/nlp_extraction_service.py` - Uses GroqClient
- `services/itinerary_service.py` - Uses GoogleMapsClient (Phase 2)
- `services/weather_service.py` - Uses WeatherClient (Phase 2)

### Uses
- `config/settings.py` - API keys and configuration
- `httpx` - Async HTTP client library

---

## Assumptions
1. API keys are valid and active
2. External APIs return JSON responses
3. Network connectivity is available
4. Rate limits are reasonable for MVP usage

## Open Questions
1. Should we implement client-side rate limiting?
2. Do we need response caching? If so, for how long?
3. Should we use connection pooling for HTTP clients?
4. What is acceptable API response time (SLA)?

---

**Last Updated**: 2026-02-07  
**Status**: Phase 1 - GroqClient Documented, Implementation Pending
