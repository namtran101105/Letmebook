# Clients Module - Human Documentation

## Overview

The `clients/` module provides wrapper classes for external API integrations. These clients handle authentication, retries, error handling, and logging for third-party services.

**Current Status**: Phase 1 - Groq client planned, implementation pending  
**Dependencies**: `httpx`, `backend.config.settings`

---

## Purpose

- Encapsulate external API communication
- Provide consistent error handling across APIs
- Implement retry logic with exponential backoff
- Log API calls for debugging and monitoring
- Abstract API details from business logic

---

## Files

### `groq_client.py` (Phase 1 - Current)

Wrapper for Groq LLM API used in NLP extraction and itinerary generation.

**Key Features**:
- Async HTTP client with configurable timeout
- Automatic retry on server errors (5xx)
- Exponential backoff (1s, 2s, 4s...)
- JSON mode support for structured responses
- Request correlation logging

**Example Usage**:
```python
from backend.clients.groq_client import GroqClient

# Initialize client
client = GroqClient(api_key=settings.GROQ_API_KEY, timeout=30, max_retries=3)

# Chat completion
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

### `gemini_client.py` (Phase 1 - Alternative)

Google Gemini API client (backup for Groq).

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

## Configuration

### API Keys

All clients use API keys from `backend/config/settings.py`:

```python
# In .env file
GROQ_API_KEY=gsk_your_key_here
GOOGLE_MAPS_API_KEY=your_key_here
WEATHER_API_KEY=your_key_here

# In code
from backend.config.settings import settings

client = GroqClient(api_key=settings.GROQ_API_KEY)
```

### Timeouts

Configure timeouts per client:

```python
# Default: 30 seconds
client = GroqClient(timeout=30)

# Shorter for fast APIs
maps_client = GoogleMapsClient(timeout=10)
```

### Retries

Configure max retry attempts:

```python
# Default: 3 retries
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

**Exponential backoff**:
- Attempt 1: Immediate
- Attempt 2: Wait 1 second
- Attempt 3: Wait 2 seconds
- Attempt 4: Wait 4 seconds

```python
sleep_time = 2 ** attempt  # 1, 2, 4, 8 seconds
```

### Example Retry Sequence

```
Request 1: ❌ 500 Internal Server Error
           Wait 1 second...
Request 2: ❌ 503 Service Unavailable  
           Wait 2 seconds...
Request 3: ✅ 200 OK - Success!
```

---

## Error Handling

### Exception Types

```python
from backend.clients.groq_client import ExternalAPIError

try:
    response = await client.chat_completion(messages)
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
    "message": "Groq API unavailable",
    "service": "Groq",
    "retry_count": 3
  }
}
```

### Common Errors

**Invalid API Key**:
```
Error: 401 Unauthorized
Cause: API key is invalid or expired
Solution: Check .env file, verify key at https://console.groq.com/keys
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
  "service": "groq_client",
  "request_id": "req-123",
  "message": "Groq API success",
  "data": {
    "tokens_used": 245,
    "response_time_ms": 1250,
    "model": "llama-3.3-70b-versatile"
  }
}
```

### Privacy Protection

API keys are **never** logged in full:
```python
# ✅ Safe logging
logger.info("API configured", extra={
    "api_key": "***...cdef"  # Only last 4 characters
})

# ❌ Dangerous - NEVER do this
logger.info(f"Using key: {api_key}")  # Full key exposed!
```

### Performance Tracking

Track API response times:
```python
import time

start = time.time()
response = await client.chat_completion(...)
duration_ms = (time.time() - start) * 1000

logger.info("API call completed", extra={
    "response_time_ms": duration_ms,
    "tokens_used": response["usage"]["total_tokens"]
})
```

---

## Testing

### Running Tests

```bash
# All client tests
pytest backend/tests/clients/ -v

# Groq client only
pytest backend/tests/clients/test_groq_client.py -v

# With coverage
pytest backend/tests/clients/ --cov=backend/clients --cov-report=html
```

### Test Types

**Unit Tests** (with mocked HTTP):
```python
@pytest.mark.asyncio
async def test_successful_api_call(mock_httpx):
    mock_httpx.post.return_value = MockResponse(200, {"result": "success"})
    
    client = GroqClient(api_key="test")
    response = await client.chat_completion(messages=[...])
    
    assert response["result"] == "success"
```

**Integration Tests** (with real API):
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_groq_api():
    """Test with actual Groq API (requires valid key)"""
    client = GroqClient()
    
    response = await client.chat_completion(
        messages=[{"role": "user", "content": "Say hello"}]
    )
    
    assert "choices" in response
    assert len(response["choices"]) > 0
```

**Negative Tests** (error scenarios):
```python
@pytest.mark.asyncio
async def test_invalid_api_key(mock_httpx):
    mock_httpx.post.return_value = MockResponse(401)
    
    client = GroqClient(api_key="invalid")
    
    with pytest.raises(ExternalAPIError) as exc:
        await client.chat_completion(messages=[...])
    
    assert exc.value.service == "Groq"
```

---

## Performance

### Response Times

**Groq API** (llama-3.3-70b-versatile):
- Simple extraction: 600-1200ms
- Complex itinerary: 1500-3000ms

**Google Maps API**:
- Geocoding: 100-300ms
- Directions: 200-500ms

**Weather API**:
- Forecast: 150-400ms

### Optimization Tips

1. **Use async/await** for concurrent API calls
2. **Cache responses** for identical requests
3. **Batch requests** when API supports it
4. **Set reasonable timeouts** (don't wait forever)
5. **Monitor token usage** (Groq charges per token)

---

## Best Practices

### When Creating Clients

1. **Use async/await** for non-blocking I/O
2. **Implement retry logic** with exponential backoff
3. **Log all API calls** with request IDs
4. **Redact sensitive data** (API keys, user PII)
5. **Handle errors gracefully** (don't crash on API failures)
6. **Support context managers** (`async with client:`)

### When Using Clients

1. **Always close clients** or use context managers
2. **Handle ExternalAPIError** in calling code
3. **Pass request_id** for correlation logging
4. **Set appropriate timeouts** for operation type
5. **Monitor API usage** and costs

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
- [ ] Implement fallback APIs

---

## API Reference

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

Call Groq chat completion API.

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
2. **Inherit pattern**: Copy GroqClient structure
3. **Add retry logic**: Use exponential backoff
4. **Add tests**: Unit + integration + negative
5. **Document**: Update CLAUDE.md and README.md
6. **Log everything**: Request start, success, failures

---

**Last Updated**: 2026-02-07  
**Maintained By**: Backend Team  
**Questions**: See `backend/clients/CLAUDE.md` for detailed agent instructions
