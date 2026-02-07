# Routes Module - Human Documentation

## Overview

The `routes/` module defines HTTP endpoints for the MonVoyage API. Routes map URLs to controller functions and handle request/response formatting, CORS, and middleware.

**Current Status**: Phase 1 - Trip routes defined, implementation pending
**LLM**: Gemini (primary) / Groq (fallback) -- all config in `settings.py`
**Dependencies**: `fastapi`, `pydantic`, `backend.controllers`

---

## Purpose

- Define RESTful API endpoints
- Map URLs to controller functions
- Validate request/response schemas
- Handle HTTP errors and status codes
- Configure CORS for frontend access
- Generate request IDs for logging

---

## Files

### `trip_routes.py` (Phase 1 - Current)

Endpoints for trip preference extraction and itinerary operations.

**Endpoints**:

#### `GET /api/health`
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "MonVoyage Trip Planner",
  "version": "1.0.0",
  "phase": "1"
}
```

#### `POST /api/extract`
Extract trip preferences from natural language using Gemini (primary) / Groq (fallback).

**TripPreferences Required Fields (10):** `city`, `country`, `start_date`, `end_date`, `duration_days`, `budget`, `budget_currency`, `interests`, `pace`, `location_preference`

**TripPreferences Optional Fields:** `starting_location` (default: from `location_preference`), `hours_per_day` (default: 8), `transportation_modes` (default: `["mixed"]`), `group_size`, `group_type`, `children_ages`, `dietary_restrictions`, `accessibility_needs`, `weather_tolerance`, `must_see_venues`, `must_avoid_venues`

**Request**:
```json
{
  "user_input": "I want to visit Kingston March 15-17 with $200 budget, interested in history and food, moderate pace"
}
```

**Response** (Success):
```json
{
  "success": true,
  "preferences": {
    "city": "Kingston",
    "country": "Canada",
    "start_date": "2026-03-15",
    "end_date": "2026-03-17",
    "duration_days": 3,
    "budget": 200.0,
    "budget_currency": "CAD",
    "interests": ["history", "food"],
    "pace": "moderate",
    "location_preference": null
  },
  "validation": {
    "valid": false,
    "issues": ["location_preference is required"],
    "warnings": [],
    "completeness_score": 0.90
  }
}
```

**Response** (Error):
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid trip preferences",
    "issues": ["Daily budget must be at least $50"]
  }
}
```

#### `POST /api/refine`
Refine existing preferences with new information using Gemini (primary) / Groq (fallback).

**Request**:
```json
{
  "preferences": {
    "city": "Kingston",
    "country": "Canada",
    "start_date": "2026-03-15",
    "end_date": "2026-03-17",
    "duration_days": 3,
    "budget": 200.0,
    "budget_currency": "CAD",
    "interests": ["history"],
    "pace": "moderate",
    "location_preference": "downtown"
  },
  "additional_input": "I'm vegetarian and interested in food too"
}
```

**Response**:
```json
{
  "success": true,
  "preferences": {
    "city": "Kingston",
    "country": "Canada",
    "start_date": "2026-03-15",
    "end_date": "2026-03-17",
    "duration_days": 3,
    "budget": 200.0,
    "budget_currency": "CAD",
    "interests": ["history", "food"],
    "pace": "moderate",
    "location_preference": "downtown",
    "dietary_restrictions": ["vegetarian"]
  },
  "validation": {
    "valid": true,
    "issues": [],
    "warnings": [],
    "completeness_score": 1.0
  }
}
```

#### `POST /api/itinerary/generate`
Generate a trip itinerary from validated preferences using Gemini (primary) / Groq (fallback).

**Request**:
```json
{
  "preferences": {
    "city": "Kingston",
    "country": "Canada",
    "start_date": "2026-03-15",
    "end_date": "2026-03-17",
    "duration_days": 3,
    "budget": 200.0,
    "budget_currency": "CAD",
    "interests": ["history", "food"],
    "pace": "moderate",
    "location_preference": "downtown"
  }
}
```

**Response**:
```json
{
  "success": true,
  "itinerary": {
    "days": [
      {
        "date": "2026-03-15",
        "activities": [...]
      }
    ],
    "budget_breakdown": {...}
  },
  "validation": {
    "valid": true,
    "issues": [],
    "warnings": []
  }
}
```

---

## HTTP Status Codes

### Success Codes
- **200 OK** - Request successful
- **201 Created** - Resource created
- **204 No Content** - Successful deletion

### Client Error Codes
- **400 Bad Request** - Invalid request body or validation failed
- **401 Unauthorized** - Missing or invalid authentication
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **429 Too Many Requests** - Rate limit exceeded

### Server Error Codes
- **500 Internal Server Error** - Unexpected server error
- **503 Service Unavailable** - External API unavailable

---

## Error Response Format

All errors return consistent format:

```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "request_id": "req_20260207_143052_a1b2c3d4",
    "additional_info": {}
  }
}
```

**Error Codes**:
- `VALIDATION_ERROR` - Input validation failed
- `EXTERNAL_API_ERROR` - Third-party service failed
- `INTERNAL_ERROR` - Unexpected server error
- `NOT_FOUND` - Resource not found
- `RATE_LIMIT_EXCEEDED` - Too many requests

---

## Request/Response Models

### Pydantic Models

**ExtractRequest**:
```python
class ExtractRequest(BaseModel):
    user_input: str
```

**RefineRequest**:
```python
class RefineRequest(BaseModel):
    preferences: Dict[str, Any]  # Must contain the 10 required TripPreferences fields
    additional_input: str
```

**GenerateItineraryRequest**:
```python
class GenerateItineraryRequest(BaseModel):
    preferences: Dict[str, Any]  # Validated TripPreferences with all 10 required fields
```

**TripResponse**:
```python
class TripResponse(BaseModel):
    success: bool
    preferences: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    itinerary: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
```

### TripPreferences Required Fields (10)
`city`, `country`, `start_date`, `end_date`, `duration_days`, `budget`, `budget_currency`, `interests`, `pace`, `location_preference`

### TripPreferences Optional Fields
`starting_location` (default: from `location_preference`), `hours_per_day` (default: 8), `transportation_modes` (default: `["mixed"]`), `group_size`, `group_type`, `children_ages`, `dietary_restrictions`, `accessibility_needs`, `weather_tolerance`, `must_see_venues`, `must_avoid_venues`

---

## CORS Configuration

CORS is configured at application level in `app.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production Settings**:
- Specify exact origins (not *)
- Enable credentials if using cookies
- Limit allowed methods to needed ones

---

## Testing

### Running Tests

```bash
# All route tests
pytest backend/tests/routes/ -v

# Specific endpoint
pytest backend/tests/routes/test_trip_routes.py::test_extract_success -v

# Integration tests (requires running server)
pytest backend/tests/routes/ --integration -v
```

### Test Client

```python
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_extract_preferences():
    response = client.post("/api/extract", json={
        "user_input": "Visit Kingston March 15-17, $200 budget, love history"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
```

### Key Test Cases

1. ✅ Health check returns 200
2. ✅ Extract with valid input returns 200
3. ✅ Extract with empty input returns 400
4. ✅ Extract with validation errors returns proper issues
5. ✅ Refine with valid data returns 200
6. ✅ Request ID is generated and logged
7. ✅ CORS headers are present
8. ✅ Error responses have consistent format

---

## Example Usage

### Using curl

```bash
# Health check
curl http://localhost:8000/api/health

# Extract preferences (Gemini primary / Groq fallback)
curl -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"user_input": "I want to visit Kingston March 15-17, budget $200 CAD, interested in history and food, moderate pace, downtown area"}'

# Refine preferences
curl -X POST http://localhost:8000/api/refine \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {
      "city": "Kingston",
      "country": "Canada",
      "start_date": "2026-03-15",
      "end_date": "2026-03-17",
      "duration_days": 3,
      "budget": 200.0,
      "budget_currency": "CAD",
      "interests": ["history", "food"],
      "pace": "moderate",
      "location_preference": "downtown"
    },
    "additional_input": "I'\''m vegetarian"
  }'

# Generate itinerary (requires all 10 required fields)
curl -X POST http://localhost:8000/api/itinerary/generate \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {
      "city": "Kingston",
      "country": "Canada",
      "start_date": "2026-03-15",
      "end_date": "2026-03-17",
      "duration_days": 3,
      "budget": 200.0,
      "budget_currency": "CAD",
      "interests": ["history", "food"],
      "pace": "moderate",
      "location_preference": "downtown"
    }
  }'
```

### Using Python requests

```python
import requests

# Extract (uses Gemini primary / Groq fallback)
response = requests.post(
    "http://localhost:8000/api/extract",
    json={"user_input": "Visit Kingston March 15-17, $200 CAD budget, history and food, moderate pace, downtown"}
)
data = response.json()
# data["preferences"] will contain the 10 required fields + any optional fields extracted

# Refine
response = requests.post(
    "http://localhost:8000/api/refine",
    json={
        "preferences": data["preferences"],
        "additional_input": "I'm vegetarian"
    }
)

# Generate itinerary (requires all 10 required fields populated)
response = requests.post(
    "http://localhost:8000/api/itinerary/generate",
    json={"preferences": data["preferences"]}
)
itinerary = response.json()["itinerary"]
```

### Using JavaScript fetch

```javascript
// Extract (uses Gemini primary / Groq fallback)
const response = await fetch('http://localhost:8000/api/extract', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    user_input: "Visit Kingston March 15-17, $200 CAD, history and food, moderate pace, downtown"
  })
});
const data = await response.json();
// data.preferences contains: city, country, start_date, end_date,
// duration_days, budget, budget_currency, interests, pace, location_preference
```

---

## Common Issues

### Issue: CORS error in browser

**Symptom**: "Access-Control-Allow-Origin" error in console

**Solution**:
1. Check CORS middleware in `app.py`
2. Ensure frontend URL is in `allow_origins`
3. Restart server after config changes

### Issue: 422 Unprocessable Entity

**Symptom**: Validation error on request body

**Solution**:
1. Check request body matches Pydantic model
2. Ensure Content-Type header is "application/json"
3. Validate JSON is properly formatted

### Issue: 500 Internal Server Error

**Symptom**: Unexpected server crash

**Solution**:
1. Check server logs for traceback
2. Verify all environment variables are set
3. Check external API connectivity (Gemini primary, Groq fallback)

---

## Best Practices

### When Creating Routes

1. **Generate request ID** at the start of each handler
2. **Use Pydantic models** for request/response validation
3. **Catch specific exceptions** before generic ones
4. **Return consistent error format**
5. **Log request start and completion**
6. **Include request_id in error responses**

### When Testing Routes

1. **Test happy path** (valid input, successful response)
2. **Test validation errors** (invalid input)
3. **Test external API failures** (mock service errors)
4. **Test edge cases** (empty strings, null values)
5. **Verify response format** (matches documented schema)

---

## Future Enhancements (Phase 2/3)

### Phase 2
- [x] Add itinerary generation endpoint (`POST /api/itinerary/generate`)
- [ ] Add venue search endpoint
- [ ] Add weather check endpoint
- [ ] Implement request rate limiting

### Phase 3
- [ ] Add budget tracking endpoints
- [ ] Add schedule adaptation endpoints
- [ ] Implement API versioning (/v1, /v2)
- [ ] Add GraphQL support

---

## API Reference

### Complete Endpoint List

**Phase 1 (Current)**:
- `GET /api/health` - Health check (reports Gemini/Groq LLM status)
- `POST /api/extract` - Extract preferences (10 required fields via Gemini/Groq)
- `POST /api/refine` - Refine preferences (Gemini/Groq)
- `POST /api/itinerary/generate` - Generate itinerary from validated preferences (Gemini/Groq)

**Phase 2 (Planned)**:
- `GET /api/venues/search` - Search venues
- `GET /api/weather/forecast` - Get weather forecast

**Phase 3 (Planned)**:
- `GET /api/budget/{trip_id}` - Get budget state
- `POST /api/budget/{trip_id}/transaction` - Record transaction
- `POST /api/itinerary/{trip_id}/adapt` - Adapt schedule

---

## Contributing

When adding new routes:

1. **Define in routes/<domain>_routes.py**
2. **Create Pydantic request/response models**
3. **Add comprehensive tests** (happy path + errors)
4. **Document in this README** with examples
5. **Update CLAUDE.md** with agent instructions
6. **Test CORS** if called from browser

---

**Last Updated**: 2026-02-07  
**Maintained By**: Backend Team  
**Questions**: See `backend/routes/CLAUDE.md` for detailed agent instructions
