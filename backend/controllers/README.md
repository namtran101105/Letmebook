# Controllers Module - Human Documentation

## Overview

The `controllers/` module contains request handlers that orchestrate business logic. Controllers sit between HTTP routes and service layer, coordinating operations without implementing business logic themselves.

**Current Status**: Phase 1 - Trip controller defined, implementation pending
**LLM**: Gemini (primary) / Groq (fallback) -- all config in `settings.py`
**Dependencies**: `backend.services`, `backend.models`, `backend.config`

---

## Purpose

- Orchestrate service calls
- Validate inputs before processing
- Format responses for routes
- Handle request/response transformation
- Coordinate multi-service operations

---

## Files

### `trip_controller.py` (Phase 1 - Current)

Handles trip preference extraction and refinement using Gemini (primary) / Groq (fallback).

**TripPreferences Required Fields (10):** `city`, `country`, `start_date`, `end_date`, `duration_days`, `budget`, `budget_currency`, `interests`, `pace`, `location_preference`

**TripPreferences Optional Fields:** `starting_location` (default: from `location_preference`), `hours_per_day` (default: 8), `transportation_modes` (default: `["mixed"]`), `group_size`, `group_type`, `children_ages`, `dietary_restrictions`, `accessibility_needs`, `weather_tolerance`, `must_see_venues`, `must_avoid_venues`

**Key Methods**:

#### `extract_preferences(user_input, request_id)`
Extracts trip preferences from natural language via Gemini (primary) / Groq (fallback).

**Example**:
```python
from controllers.trip_controller import TripController

controller = TripController()
result = await controller.extract_preferences(
    user_input="I want to visit Kingston March 15-17, budget $200 CAD, history and food, moderate pace, downtown",
    request_id="req_20260207_143052_abc123"
)

# Returns:
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
    },
    "validation": {
        "valid": True,
        "issues": [],
        "warnings": [],
        "completeness_score": 1.0
    }
}
```

#### `refine_preferences(existing_preferences, additional_input, request_id)`
Refines existing preferences with new information via Gemini (primary) / Groq (fallback).

**Example**:
```python
result = await controller.refine_preferences(
    existing_preferences={
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
    additional_input="I'm vegetarian and also interested in food",
    request_id="req_20260207_143053_def456"
)

# Returns updated preferences with dietary_restrictions (optional) and updated interests
```

### `itinerary_controller.py` (Phase 1 - Added)

Handles itinerary generation using Gemini (primary) / Groq (fallback).

**Key Methods**:

#### `generate_itinerary(preferences, request_id)`
Generates a trip itinerary from validated preferences (all 10 required fields must be present).

**Example**:
```python
from controllers.itinerary_controller import ItineraryController

controller = ItineraryController()
result = await controller.generate_itinerary(
    preferences={
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
    request_id="req_20260207_143054_ghi789"
)

# Returns itinerary with days, activities, and budget breakdown
```

---

## Controller Pattern

### Responsibilities

**Controllers SHOULD**:
- Orchestrate service calls
- Validate inputs
- Format responses
- Log operations
- Propagate errors with context

**Controllers SHOULD NOT**:
- Implement business logic (belongs in services)
- Access databases directly (use services/storage)
- Handle HTTP concerns (belongs in routes)
- Transform complex data (use dedicated transformers)

### Design Pattern

```
Route → Controller → Service → Gemini (primary) / Groq (fallback)
         ↓
         ↓ Orchestration (validate 10 required fields, apply optional defaults)
         ↓
         ↓ Response Formatting
         ↓
Route ← Controller ← Service ← Data
```

---

## Response Format

All controller methods return consistent structure:

```python
{
    "preferences": {...},      # Main data (as dict)
    "validation": {...},       # Validation results
    "metadata": {...}          # Optional metadata
}
```

**Why dicts not models?**
- Routes need JSON-serializable data
- Easier to transform for different API versions
- Models stay internal to backend

---

## Error Handling

### Controllers Log and Re-Raise

```python
try:
    preferences = await self.nlp_service.extract_preferences(...)
except ExternalAPIError as e:
    self.logger.error("NLP service failed", extra={
        "request_id": request_id,
        "service": e.service
    }, exc_info=True)
    raise  # Routes handle HTTP status
```

### Routes Convert to HTTP Errors

```python
# In routes/trip_routes.py
try:
    result = await controller.extract_preferences(...)
except ExternalAPIError:
    raise HTTPException(status_code=503, detail=...)
```

---

## Testing

### Running Tests

```bash
# All controller tests
pytest backend/tests/controllers/ -v

# Specific controller
pytest backend/tests/controllers/test_trip_controller.py -v

# With coverage
pytest backend/tests/controllers/ --cov=backend/controllers --cov-report=html
```

### Test Structure

```python
import pytest
from unittest.mock import Mock, AsyncMock
from controllers.trip_controller import TripController

@pytest.fixture
def mock_nlp_service():
    """Mock NLP service for testing"""
    service = Mock()
    service.extract_preferences = AsyncMock()
    service.refine_preferences = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_extract_preferences_success(mock_nlp_service):
    """Test successful extraction"""
    controller = TripController()
    controller.nlp_service = mock_nlp_service
    
    # Setup mock with all 10 required fields
    mock_prefs = TripPreferences(
        city="Kingston", country="Canada",
        start_date="2026-03-15", end_date="2026-03-17",
        duration_days=3, budget=200.0, budget_currency="CAD",
        interests=["history"], pace="moderate",
        location_preference="downtown"
    )
    mock_nlp_service.extract_preferences.return_value = mock_prefs

    # Call controller
    result = await controller.extract_preferences(
        user_input="Visit Kingston...",
        request_id="req-123"
    )

    # Assertions - verify required fields
    assert result["preferences"]["city"] == "Kingston"
    assert result["preferences"]["start_date"] == "2026-03-15"
    assert result["preferences"]["duration_days"] == 3
    assert "validation" in result
```

### Key Test Cases

1. ✅ Extract preferences (success)
2. ✅ Extract preferences (validation warning)
3. ✅ Refine preferences (add interest)
4. ✅ Refine preferences (add dietary restriction)
5. ✅ Refine preferences (preserve existing fields)
6. ✅ Service initialization
7. ✅ Response formatting
8. ✅ Error propagation
9. ✅ Request ID logging
10. ✅ Multiple refinements

---

## Request ID Propagation

### Purpose
Request IDs enable tracing a single request through all layers.

### Flow
```
Route (generates req_xyz) 
  → Controller (receives req_xyz, logs with it, passes to service)
    → Service (receives req_xyz, logs with it, passes to client)
      → Client (receives req_xyz, logs with it, sends to API)
```

### Example
```python
# In controller
logger.info("Extracting preferences", extra={
    "request_id": request_id,  # Always include
    "controller": "trip"
})

await self.nlp_service.extract_preferences(
    user_input=user_input,
    request_id=request_id  # Always pass
)
```

---

## Common Issues

### Issue: Controller implementing business logic

**Symptom**: Complex logic in controller methods

**Solution**: Extract to service
```python
# ❌ BAD - Controller implements logic
class TripController:
    async def extract_preferences(self, user_input, request_id):
        # Complex parsing logic here
        parsed = self._parse_dates(user_input)
        validated = self._validate_budget(parsed)
        ...

# ✅ GOOD - Controller orchestrates
class TripController:
    async def extract_preferences(self, user_input, request_id):
        preferences = await self.nlp_service.extract_preferences(
            user_input, request_id
        )
        validation = preferences.validate()
        return {"preferences": preferences.to_dict(), "validation": validation}
```

### Issue: Controller handling HTTP concerns

**Symptom**: HTTPException raised in controller

**Solution**: Raise domain exceptions, let routes handle HTTP
```python
# ❌ BAD
class TripController:
    async def extract_preferences(self, ...):
        if not user_input:
            raise HTTPException(status_code=400, detail="Input required")

# ✅ GOOD
class TripController:
    async def extract_preferences(self, ...):
        if not user_input:
            raise ValidationError("Input required")

# In routes
try:
    result = await controller.extract_preferences(...)
except ValidationError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

### Issue: Controller accessing database

**Symptom**: Database imports in controller

**Solution**: Use storage/repository layer
```python
# ❌ BAD
from storage.database import db

class TripController:
    async def save_trip(self, preferences):
        db.trips.insert_one(preferences)

# ✅ GOOD
class TripController:
    def __init__(self):
        self.trip_repo = TripRepository()
    
    async def save_trip(self, preferences):
        await self.trip_repo.save(preferences)
```

---

## Best Practices

### 1. Keep Controllers Thin
Controllers should be 20-50 lines per method. If longer, extract logic to services.

### 2. Consistent Response Format
All methods return same structure:
```python
{
    "data": {...},
    "validation": {...},
    "metadata": {...}
}
```

### 3. Always Propagate Request ID
```python
async def method(self, arg, request_id: str):
    logger.info("...", extra={"request_id": request_id})
    await service.method(arg, request_id=request_id)
```

### 4. Log Operations
```python
logger.info("Operation started", extra={"request_id": ...})
# ... operation ...
logger.info("Operation completed", extra={"request_id": ...})
```

### 5. Convert Models to Dicts
```python
# Return dicts, not models
return {
    "preferences": preferences.to_dict(),  # Not preferences
    "validation": validation
}
```

---

## Future Enhancements (Phase 2/3)

### Phase 2
- [x] Itinerary controller for generation/retrieval (Gemini primary / Groq fallback)
- [ ] Venue controller for search operations
- [ ] Weather controller for forecast integration

### Phase 3
- [ ] Budget controller for spending tracking
- [ ] Schedule controller for adaptation
- [ ] Notification controller for alerts

---

## Integration Points

### Used By
- `routes/trip_routes.py` - HTTP endpoints

### Uses
- `services/nlp_extraction_service.py` - NLP extraction logic (Gemini primary / Groq fallback)
- `services/itinerary_service.py` - Itinerary generation logic (Gemini primary / Groq fallback)
- `models/trip_preferences.py` - Data models (10 required + optional fields)
- `config/settings.py` - All LLM configuration (Gemini + Groq, no separate gemini.py)
- `storage/trip_json_repo.py` - Data persistence (Phase 2)

---

## Example: Full Request Flow

### 1. Route receives request
```python
@router.post("/extract")
async def extract_preferences(request: ExtractRequest):
    request_id = generate_request_id()
    result = await trip_controller.extract_preferences(
        user_input=request.user_input,
        request_id=request_id
    )
    return result
```

### 2. Controller orchestrates
```python
async def extract_preferences(self, user_input, request_id):
    logger.info("Extracting", extra={"request_id": request_id})
    preferences = await self.nlp_service.extract_preferences(
        user_input, request_id
    )
    validation = preferences.validate()
    return {"preferences": preferences.to_dict(), "validation": validation}
```

### 3. Service implements logic
```python
async def extract_preferences(self, user_input, request_id):
    logger.debug("Calling Gemini API (primary)", extra={"request_id": request_id})
    try:
        response = await self.gemini_client.chat_completion(...)
    except Exception:
        logger.warning("Gemini failed, falling back to Groq", extra={"request_id": request_id})
        response = await self.groq_client.chat_completion(...)
    preferences = self._parse_response(response)
    return preferences
```

### 4. Controller returns to route
```python
# Route receives formatted response
{
    "preferences": {...},
    "validation": {...}
}
```

### 5. Route sends HTTP response
```python
# Client receives JSON
200 OK
{
    "success": true,
    "preferences": {...},
    "validation": {...}
}
```

---

## Contributing

When adding new controllers:

1. **Define responsibility** - What does this controller orchestrate?
2. **Create thin methods** - Orchestrate, don't implement
3. **Add comprehensive tests** - Mock dependencies
4. **Document in README** - Add examples and test cases
5. **Update CLAUDE.md** - Add agent instructions
6. **Test integration** - Verify full request flow

---

**Last Updated**: 2026-02-07  
**Maintained By**: Backend Team  
**Questions**: See `backend/controllers/CLAUDE.md` for detailed agent instructions
