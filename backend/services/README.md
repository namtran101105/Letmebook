# Services Module - Human Documentation

## Overview

The `services/` module contains business logic for trip planning operations. It orchestrates data extraction, validation, itinerary generation, budget tracking, and schedule adaptation.

**Current Status**: Phase 1 - NLP extraction implemented, other services planned  
**Dependencies**: `backend.clients`, `backend.models`, `backend.config`

---

## Purpose

- Extract structured trip preferences from natural language
- Generate feasible multi-day itineraries
- Track real-time budget spending
- Adapt schedules when users run late or skip activities
- Integrate weather forecasts into planning
- Filter venues by interests, budget, and accessibility

---

## Files

### `nlp_extraction_service.py` (Phase 1 - Current)

Extracts structured `TripPreferences` from natural language user input using Groq LLM.

**Key Class**: `NLPExtractionService`

**Main Operations**:
1. **Initial Extraction** - Extract from first user message
2. **Refinement** - Update preferences with additional information

**Example Usage**:
```python
from backend.services.nlp_extraction_service import NLPExtractionService
from backend.clients.groq_client import GroqClient

# Initialize
groq_client = GroqClient(api_key=settings.GROQ_API_KEY)
nlp_service = NLPExtractionService(groq_client)

# Extract preferences
user_input = "I want to visit Kingston March 15-17 with $200 budget. Love history and food."
preferences = await nlp_service.extract_preferences(user_input, request_id="req-123")

# Refine with additional info
additional = "I'm vegetarian and need wheelchair access"
updated = await nlp_service.refine_preferences(preferences, additional, request_id="req-124")
```

**Conservative Extraction**:
- Only extracts explicitly mentioned information
- Uses `null` for missing data (never guesses)
- Validates against TripPreferences schema

### `itinerary_service.py` (Phase 2 - Planned)

Generates feasible daily schedules from validated preferences.

**Key Features**:
- Venue filtering by interests and budget
- Multi-modal transportation routing
- Pace-based activity scheduling (relaxed/moderate/packed)
- Meal scheduling with dietary restrictions
- Weather-aware planning (outdoor activity warnings)

### `budget_service.py` (Phase 3 - Planned)

Real-time budget tracking with overspend alerts.

### `adaptation_service.py` (Phase 3 - Planned)

Re-optimizes itinerary when users run late or skip activities.

### `weather_service.py` (Phase 2 - Planned)

Fetches weather forecasts and provides activity recommendations.

### `venue_service.py` (Phase 2 - Planned)

Filters and ranks Kingston venues based on user preferences.

---

## NLP Extraction Details

### Extraction Process

1. **Build Prompt**: Create extraction prompt with JSON schema
2. **Call Groq API**: Send prompt with `response_format={"type": "json_object"}`
3. **Parse Response**: Extract JSON from LLM response
4. **Create Model**: Convert JSON to `TripPreferences` dataclass
5. **Validate**: Check required fields and business rules

### System Instruction

The NLP service uses this system instruction:

> "You are a travel planning assistant that extracts structured information from natural language. Extract explicit information mentioned by the user. Infer reasonable defaults only when strongly implied. Use null for truly missing information. Return valid JSON only. Be conservative - only extract what the user clearly communicated."

### JSON Schema

The extraction prompt includes this schema:
```json
{
  "starting_location": "string or null",
  "city": "string (default: Kingston)",
  "start_date": "string YYYY-MM-DD or null",
  "end_date": "string YYYY-MM-DD or null",
  "budget": "number or null",
  "interests": "array of strings",
  "hours_per_day": "number or null",
  "transportation_modes": "array of strings",
  "pace": "string (relaxed|moderate|packed) or null",
  "group_size": "number or null",
  "dietary_restrictions": "array of strings",
  "accessibility_needs": "array of strings",
  "weather_tolerance": "string or null"
}
```

### Refinement Process

When refining existing preferences:
1. Include previous extraction in prompt
2. Ask LLM to merge new information
3. Preserve existing values unless contradicted
4. Maintain trip_id and timestamps

**Example**:
```python
# Initial
"I want to visit Kingston next weekend"
→ {"start_date": "2026-02-13", "end_date": "2026-02-15"}

# Refinement
"Actually make it a 3-day trip and I'm vegetarian"
→ {"start_date": "2026-02-13", "end_date": "2026-02-16", "dietary_restrictions": ["vegetarian"]}
```

---

## Error Handling

### Retry Logic

Groq API calls retry up to 3 times with exponential backoff:
- Attempt 1: Immediate
- Attempt 2: Wait 1 second
- Attempt 3: Wait 2 seconds
- Attempt 4: Wait 4 seconds
- Failed: Raise `ExternalAPIError`

### Common Errors

**Invalid JSON Response**:
```
Error: Groq returned invalid JSON
Cause: LLM didn't return valid JSON despite json_object mode
Solution: Retry (usually succeeds on retry)
```

**Network Timeout**:
```
Error: Connection timeout to Groq API
Cause: Network issues or API overload
Solution: Automatic retry with backoff
```

**Validation Failure**:
```
Error: Extracted data invalid (e.g., budget < $50/day)
Cause: User provided insufficient budget
Solution: Return validation errors to user
```

---

## Logging

### Log Levels

**INFO**: Request start, extraction success, validation results
```json
{
  "level": "INFO",
  "message": "NLP extraction successful",
  "request_id": "req-123",
  "fields_extracted": 12,
  "completeness_score": 0.85
}
```

**WARNING**: Tight budget, retries, degraded functionality
```json
{
  "level": "WARNING",
  "message": "Budget is tight",
  "request_id": "req-123",
  "daily_budget": 55.0,
  "impact": "Will prioritize affordable options"
}
```

**ERROR**: API failures, invalid responses, validation errors
```json
{
  "level": "ERROR",
  "message": "Groq API failed",
  "request_id": "req-123",
  "retry_count": 1,
  "error": "Connection timeout"
}
```

### Privacy Protection

User input is **never** logged in full. Only metadata:
```python
# ✅ Good
logger.info("Processing user input", extra={
    "request_id": "req-123",
    "input_length": 150,
    "intent": "trip_planning"
})

# ❌ Bad - NEVER do this
logger.info("User said: " + user_input)  # May contain PII
```

---

## Testing

### Running Tests

```bash
# All services tests
pytest backend/tests/services/ -v

# NLP extraction only
pytest backend/tests/services/test_nlp_extraction_service.py -v

# With coverage
pytest backend/tests/services/ --cov=backend/services --cov-report=html
```

### Test Coverage Requirements

- **NLP Service**: 95% coverage
- **Validation Orchestration**: 100% coverage
- **Error Handling**: 100% coverage

### Key Test Scenarios

#### Extraction Tests
1. ✅ Complete input (all fields provided)
2. ✅ Minimal input (only required fields)
3. ✅ Budget as total (convert to daily)
4. ✅ Budget as daily
5. ✅ Multiple interests
6. ✅ Dietary restrictions
7. ✅ Accessibility needs
8. ✅ Transportation modes
9. ✅ Pace preference

#### Refinement Tests
10. ✅ Add dietary restriction
11. ✅ Update budget
12. ✅ Add must-see venues
13. ✅ Preserve existing fields

#### Error Handling Tests
14. ❌ Empty user input
15. ❌ Invalid JSON from API
16. ❌ Network timeout (with retry)
17. ❌ Max retries exceeded
18. ❌ Invalid extracted data

---

## Performance

### Response Times

**Target**: < 2 seconds for extraction  
**Typical**: 800ms - 1.5s

Breakdown:
- Groq API call: 600-1200ms
- JSON parsing: 10-50ms
- Validation: 50-100ms
- Logging: 10-20ms

### Optimization Tips

1. **Use async/await** for concurrent operations
2. **Cache** Groq API responses for identical inputs
3. **Batch** multiple refinements if possible
4. **Reduce temperature** (0.2) for faster, deterministic responses

---

## Integration with Other Modules

### Calls
- `clients.groq_client.GroqClient` - LLM API calls
- `models.trip_preferences.TripPreferences` - Data validation

### Called By
- `controllers.trip_controller` - HTTP request handlers
- `routes.trip_routes` - API endpoints

### Data Flow
```
User Input (HTTP)
    ↓
routes/trip_routes.py
    ↓
controllers/trip_controller.py
    ↓
services/nlp_extraction_service.py
    ↓
clients/groq_client.py → Groq API
    ↓
models/trip_preferences.py (validation)
    ↓
HTTP Response (JSON)
```

---

## Common Issues

### Issue: "Groq API timeout"

**Cause**: Network latency or API overload

**Solution**:
- Automatic retry (up to 3 attempts)
- Check Groq status: https://status.groq.com
- Verify network connectivity

### Issue: "Invalid JSON from Groq"

**Cause**: LLM returned text instead of JSON

**Solution**:
- Usually resolved by retry
- Check if `response_format={"type": "json_object"}` is set
- Verify system instruction includes "Return valid JSON only"

### Issue: "Completeness score always low"

**Cause**: User input lacks required information

**Solution**:
- Guide user with follow-up questions
- Check validation response for missing fields
- Use refinement to add missing data incrementally

---

## Future Enhancements (Phase 2/3)

### Phase 2
- [ ] Implement itinerary generation service
- [ ] Implement venue filtering service
- [ ] Implement weather integration service
- [ ] Add caching for Groq API responses

### Phase 3
- [ ] Implement budget tracking service
- [ ] Implement schedule adaptation service
- [ ] Add multi-language support for extraction
- [ ] Implement batch extraction for multiple users

---

## Best Practices

### When Using NLP Service

1. **Always validate** extracted preferences before using
2. **Handle validation errors** gracefully (return to user, don't crash)
3. **Log request IDs** for correlation across services
4. **Redact user input** in logs (privacy protection)
5. **Use refinement** for incremental information gathering

### Prompt Engineering

1. **Be specific** in extraction schema
2. **Include examples** in system instruction if needed
3. **Keep temperature low** (0.2) for consistent extraction
4. **Use JSON mode** (`response_format={"type": "json_object"}`)

---

## API Reference

### `NLPExtractionService`

**Constructor**:
```python
NLPExtractionService(groq_client: GroqClient)
```

**Methods**:

**`async extract_preferences(user_input: str, request_id: str) -> TripPreferences`**

Extracts trip preferences from natural language.

- **Args**:
  - `user_input`: Raw user message
  - `request_id`: UUID for correlation
- **Returns**: `TripPreferences` object
- **Raises**: `ExternalAPIError`, `ValidationError`

**`async refine_preferences(existing: TripPreferences, additional: str, request_id: str) -> TripPreferences`**

Updates preferences with new information.

- **Args**:
  - `existing`: Current preferences
  - `additional`: New user input
  - `request_id`: UUID for correlation
- **Returns**: Updated `TripPreferences`
- **Raises**: `ExternalAPIError`

---

## Contributing

When adding new services:

1. **Follow naming convention**: `<domain>_service.py`
2. **Add comprehensive tests** (95%+ coverage)
3. **Document in CLAUDE.md** (agent instructions)
4. **Document in README.md** (human guide)
5. **Add logging** with request correlation
6. **Handle errors** with retry logic

---

**Last Updated**: 2026-02-07  
**Maintained By**: Backend Team  
**Questions**: See `backend/services/CLAUDE.md` for detailed agent instructions
