# Clients Module - Human Documentation

## Overview

The `clients/` module provides wrapper classes for external API integrations. These clients handle authentication, retries, error handling, and logging for third-party services. Gemini is the primary LLM, with Groq available as a fallback.

**Current Status**: Phase 1 - GeminiClient (primary) and GroqClient (fallback) implemented
**Dependencies**: `google-genai`, `httpx`, `backend.config.settings`

---

## Purpose

- Encapsulate external API communication
- Provide consistent error handling across APIs
- Implement retry logic with exponential backoff
- Log API calls for debugging and monitoring
- Abstract API details from business logic
- Support LLM fallback (Gemini primary, Groq fallback)

---

## Files

### `gemini_client.py` (Phase 1 - Primary LLM)

Wrapper for Google Gemini API using the `google-genai` SDK. This is the primary LLM client used for NLP extraction and itinerary generation.

**Key Features**:
- Uses `from google import genai` (google-genai SDK)
- Simple `generate_content` interface returning plain text
- Configurable temperature and max tokens per request
- System instruction support
- Request correlation logging

**Example Usage**:
```python
from backend.clients.gemini_client import GeminiClient
from backend.config.settings import settings

# Initialize client
client = GeminiClient(
    api_key=settings.GEMINI_KEY,
    model=settings.GEMINI_MODEL
)

# Generate content for NLP extraction
result = await client.generate_content(
    prompt="Extract trip preferences from: I want to visit Kingston March 15-17...",
    system_instruction="You are a travel planning assistant that extracts structured information.",
    temperature=settings.GEMINI_EXTRACTION_TEMPERATURE,
    max_tokens=settings.GEMINI_EXTRACTION_MAX_TOKENS,
    request_id="req-123"
)

# result is a plain string containing the LLM response
print(result)

# Generate content for itinerary
itinerary_result = await client.generate_content(
    prompt="Generate a 3-day itinerary for Kingston...",
    system_instruction="You are an itinerary planning engine.",
    temperature=settings.GEMINI_ITINERARY_TEMPERATURE,
    max_tokens=settings.GEMINI_ITINERARY_MAX_TOKENS,
    request_id="req-456"
)
```

### `groq_client.py` (Phase 1 - Fallback LLM)

Wrapper for Groq LLM API used as fallback when Gemini is unavailable.

**Key Features**:
- Async HTTP client with configurable timeout
- Automatic retry on server errors (5xx)
- Exponential backoff (1s, 2s, 4s...)
- JSON mode support for structured responses
- Request correlation logging

**Example Usage**:
```python
from backend.clients.groq_client import GroqClient
from backend.config.settings import settings

# Initialize client (only when needed as fallback)
client = GroqClient(
    api_key=settings.GROQ_API_KEY,
    timeout=30,
    max_retries=3
)

# Chat completion (fallback)
response = await client.chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Extract trip preferences from: I want to visit Kingston..."}
    ],
    model="llama-3.3-70b-versatile",
    temperature=0.2,
    response_format={"type": "json_object"},
    request_id="req-123"
)

# Access response
content = response["choices"][0]["message"]["content"]
tokens_used = response["usage"]["total_tokens"]

# Close client
await client.close()

# Or use as context manager
async with GroqClient() as client:
    response = await client.chat_completion(...)
```

### `google_maps_client.py` (Phase 2 - Planned)

Google Maps API for geocoding and routing.

**Planned Features**:
- Geocode addresses to coordinates
- Calculate distance matrix between venues
- Get turn-by-turn directions
- Estimate travel times by mode (car/transit/walking)

### `weather_client.py` (Phase 2 - Planned)

Weather API for forecasts and activity recommendations.

**Planned Features**:
- 7-day hourly forecasts
- Outdoor activity safety checks
- Precipitation warnings
- Temperature and conditions

---

## LLM Client Strategy

### Primary: Gemini
- Used for all NLP extraction and itinerary generation
- Configured via `GEMINI_KEY`, `GEMINI_MODEL` in settings
- Uses `google-genai` SDK (`from google import genai`)
- Separate temperature settings for extraction (0.2) and itinerary (0.7)

### Fallback: Groq
- Used only when Gemini is unavailable or fails
- Configured via `GROQ_API_KEY`, `GROQ_MODEL` in settings
- Uses `httpx` for direct API calls
- JSON mode support via `response_format`

### Fallback Flow
```
Request comes in
    |
    v
Try Gemini (primary)
    |
    +-- Success --> Return result
    |
    +-- Failure --> Log warning
                    |
                    v
                Try Groq (fallback)
                    |
                    +-- Success --> Return result
                    |
                    +-- Failure --> Raise ExternalAPIError
```

---

## Configuration

### API Keys

All clients use API keys from `backend/config/settings.py`:

```python
# In .env file
GEMINI_KEY=your_gemini_key_here
GROQ_API_KEY=gsk_your_groq_key_here   # Optional fallback
GOOGLE_MAPS_API_KEY=your_key_here      # Phase 2
WEATHER_API_KEY=your_key_here          # Phase 2

# In code
from backend.config.settings import settings

gemini_client = GeminiClient(api_key=settings.GEMINI_KEY)
groq_client = GroqClient(api_key=settings.GROQ_API_KEY)  # Only if fallback needed
```

### Timeouts

Configure timeouts per client:

```python
# Default: 30 seconds for LLM APIs
groq_client = GroqClient(timeout=30)

# Shorter for fast APIs
maps_client = GoogleMapsClient(timeout=10)
```

### Retries

Configure max retry attempts:

```python
# Default: 3 retries (Groq only -- Gemini uses SDK defaults)
client = GroqClient(max_retries=3)

# More retries for critical operations
client = GroqClient(max_retries=5)
```

---

## Retry Logic

### When to Retry

**Retry (5xx Server Errors)**:
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable
- 504 Gateway Timeout

**Do NOT Retry (4xx Client Errors)**:
- 400 Bad Request - Fix the payload
- 401 Unauthorized - Fix the API key
- 403 Forbidden - Check permissions
- 404 Not Found - Check the endpoint

**Special Case**:
- 429 Too Many Requests - Wait and retry once

### Backoff Strategy

**Exponential backoff** (Groq client):
- Attempt 1: Immediate
- Attempt 2: Wait 1 second
- Attempt 3: Wait 2 seconds
- Attempt 4: Wait 4 seconds

```python
sleep_time = 2 ** attempt  # 1, 2, 4, 8 seconds
```

### Example Retry Sequence

```
Gemini Request: Failure (timeout)
    --> Fall back to Groq
Groq Request 1: 500 Internal Server Error
    --> Wait 1 second...
Groq Request 2: 503 Service Unavailable
    --> Wait 2 seconds...
Groq Request 3: 200 OK - Success!
```

---

## Error Handling

### Exception Types

```python
from backend.clients.groq_client import ExternalAPIError

try:
    # Try Gemini first
    result = await gemini_client.generate_content(prompt, request_id=req_id)
except ExternalAPIError:
    # Fall back to Groq
    try:
        response = await groq_client.chat_completion(messages, request_id=req_id)
        result = response["choices"][0]["message"]["content"]
    except ExternalAPIError as e:
        print(f"API: {e.service}")       # "Groq"
        print(f"Error: {e.error}")       # "Connection timeout"
        print(f"Retries: {e.retry_count}")  # 3
```

### Error Response Format

When API fails:
```json
{
  "success": false,
  "error": {
    "code": "EXTERNAL_API_ERROR",
    "message": "All LLM providers unavailable",
    "services_tried": ["Gemini", "Groq"],
    "last_error": "Connection timeout"
  }
}
```

### Common Errors

**Invalid API Key**:
```
Error: 401 Unauthorized
Cause: API key is invalid or expired
Solution: Check .env file, verify GEMINI_KEY or GROQ_API_KEY
```

**Rate Limited**:
```
Error: 429 Too Many Requests
Cause: Exceeded API rate limit
Solution: Wait before retrying, implement request throttling
```

**Timeout**:
```
Error: Connection timeout after 30s
Cause: API is slow or unresponsive
Solution: Increase timeout or check API status
```

**Network Error**:
```
Error: Connection failed
Cause: No internet connection or API is down
Solution: Check network, verify API status page
```

---

## Logging

### Log Structure

All API calls are logged with:
```json
{
  "timestamp": "2026-02-07T10:30:45Z",
  "level": "INFO",
  "service": "gemini_client",
  "request_id": "req-123",
  "message": "Gemini API success",
  "data": {
    "response_length": 1200,
    "model": "gemini-2.0-flash"
  }
}
```

### Privacy Protection

API keys are **never** logged in full:
```python
# Safe logging
logger.info("API configured", extra={
    "api_key": "***...cdef"  # Only last 4 characters
})

# Dangerous - NEVER do this
logger.info(f"Using key: {api_key}")  # Full key exposed!
```

### Performance Tracking

Track API response times:
```python
import time

start = time.time()
result = await gemini_client.generate_content(prompt, request_id=req_id)
duration_ms = (time.time() - start) * 1000

logger.info("API call completed", extra={
    "response_time_ms": duration_ms,
    "llm": "Gemini",
    "model": "gemini-2.0-flash"
})
```

---

## Testing

### Running Tests

```bash
# All client tests
pytest backend/tests/clients/ -v

# Gemini client only
pytest backend/tests/clients/test_gemini_client.py -v

# Groq client only
pytest backend/tests/clients/test_groq_client.py -v

# With coverage
pytest backend/tests/clients/ --cov=backend/clients --cov-report=html
```

### Test Types

**Unit Tests** (with mocked APIs):
```python
@pytest.mark.asyncio
async def test_gemini_successful_generation():
    client = GeminiClient(api_key="test_key")

    with mock.patch.object(client.client.models, 'generate_content') as mock_gen:
        mock_gen.return_value = MockGeminiResponse(text="Generated itinerary")

        result = await client.generate_content(
            prompt="Generate itinerary",
            temperature=0.7,
            request_id="req-123"
        )

    assert result == "Generated itinerary"
```

**Integration Tests** (with real API):
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_gemini_api():
    """Test with actual Gemini API (requires valid key)"""
    client = GeminiClient()

    result = await client.generate_content(
        prompt="Say hello",
        temperature=0.2,
        max_tokens=100,
        request_id="test-integration"
    )

    assert isinstance(result, str)
    assert len(result) > 0
```

**Negative Tests** (error scenarios):
```python
@pytest.mark.asyncio
async def test_gemini_missing_key():
    with pytest.raises(ValueError, match="Gemini API key required"):
        GeminiClient(api_key="")

@pytest.mark.asyncio
async def test_groq_invalid_api_key(mock_httpx):
    mock_httpx.post.return_value = MockResponse(401)

    client = GroqClient(api_key="invalid")

    with pytest.raises(ExternalAPIError) as exc:
        await client.chat_completion(messages=[...])

    assert exc.value.service == "Groq"
```

---

## Performance

### Response Times

**Gemini API** (gemini-2.0-flash):
- Simple extraction: 500-1000ms
- Complex itinerary: 1000-2500ms

**Groq API** (llama-3.3-70b-versatile) - fallback:
- Simple extraction: 600-1200ms
- Complex itinerary: 1500-3000ms

**Google Maps API**:
- Geocoding: 100-300ms
- Directions: 200-500ms

**Weather API**:
- Forecast: 150-400ms

### Optimization Tips

1. **Use Gemini as primary** for faster responses
2. **Use async/await** for concurrent API calls
3. **Cache responses** for identical requests
4. **Batch requests** when API supports it
5. **Set reasonable timeouts** (don't wait forever)
6. **Monitor token usage** (both Gemini and Groq charge per token)

---

## Best Practices

### When Creating Clients

1. **Use async/await** for non-blocking I/O
2. **Implement retry logic** with exponential backoff
3. **Log all API calls** with request IDs
4. **Redact sensitive data** (API keys, user PII)
5. **Handle errors gracefully** (don't crash on API failures)
6. **Support fallback** where appropriate

### When Using Clients

1. **Try Gemini first**, then Groq as fallback
2. **Always close clients** or use context managers
3. **Handle ExternalAPIError** in calling code
4. **Pass request_id** for correlation logging
5. **Set appropriate timeouts** for operation type
6. **Monitor API usage** and costs

---

## Future Enhancements (Phase 2/3)

### Phase 2
- [ ] Implement GoogleMapsClient
- [ ] Implement WeatherClient
- [ ] Add response caching
- [ ] Add request throttling

### Phase 3
- [ ] Implement connection pooling
- [ ] Add circuit breaker pattern
- [ ] Add API usage metrics
- [ ] Improve fallback logic with health checks

---

## API Reference

### `GeminiClient`

**Constructor**:
```python
GeminiClient(
    api_key: Optional[str] = None,
    model: Optional[str] = None
)
```

**Methods**:

**`async generate_content(prompt, system_instruction, temperature, max_tokens, request_id) -> str`**

Generate content using Gemini API.

- **Args**:
  - `prompt`: The user prompt to send
  - `system_instruction`: Optional system instruction
  - `temperature`: Sampling temperature 0-1 (optional)
  - `max_tokens`: Max response tokens (optional)
  - `request_id`: UUID for logging
- **Returns**: Generated text as string
- **Raises**: `ExternalAPIError`

### `GroqClient`

**Constructor**:
```python
GroqClient(
    api_key: Optional[str] = None,
    timeout: int = 30,
    max_retries: int = 3
)
```

**Methods**:

**`async chat_completion(...) -> Dict[str, Any]`**

Call Groq chat completion API (fallback).

- **Args**:
  - `messages`: List of chat messages
  - `model`: Model name (optional)
  - `temperature`: Sampling temperature 0-1 (optional)
  - `max_tokens`: Max response tokens (optional)
  - `response_format`: `{"type": "json_object"}` for JSON mode
  - `request_id`: UUID for logging
- **Returns**: API response dict
- **Raises**: `ExternalAPIError`

**`async close()`**

Close HTTP client and release resources.

**Context Manager**:
```python
async with GroqClient() as client:
    response = await client.chat_completion(...)
# Client automatically closed
```

---

## Contributing

When adding new clients:

1. **Follow naming**: `<service>_client.py`
2. **Inherit pattern**: Copy GeminiClient or GroqClient structure
3. **Add retry logic**: Use exponential backoff
4. **Add tests**: Unit + integration + negative
5. **Document**: Update CLAUDE.md and README.md
6. **Log everything**: Request start, success, failures

---

**Last Updated**: 2026-02-07
**Maintained By**: Backend Team
**Questions**: See `backend/clients/CLAUDE.md` for detailed agent instructions
