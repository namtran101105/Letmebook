# Services Module - Human Documentation

## Overview

The `services/` module contains business logic for trip planning operations. It orchestrates data extraction, validation, itinerary generation, budget tracking, and schedule adaptation.

**Current Status**: Phase 1 - NLP extraction and itinerary generation implemented
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

Extracts structured `TripPreferences` from natural language user input using Gemini (primary) or Groq (fallback) LLM.

**Key Class**: `NLPExtractionService`

**Main Operations**:
1. **Initial Extraction** - Extract from first user message using Gemini
2. **Refinement** - Update preferences with additional information
3. **Fallback** - Use Groq if Gemini is unavailable

**Example Usage**:
```python
from backend.services.nlp_extraction_service import NLPExtractionService
from backend.clients.gemini_client import GeminiClient
from backend.clients.groq_client import GroqClient

# Initialize with Gemini (primary) and optional Groq (fallback)
gemini_client = GeminiClient(api_key=settings.GEMINI_KEY)
groq_client = GroqClient(api_key=settings.GROQ_API_KEY)  # Optional
nlp_service = NLPExtractionService(gemini_client, groq_client)

# Extract preferences (tries Gemini first, falls back to Groq)
user_input = "I want to visit downtown Kingston March 15-17 with $200 budget. Love history and food."
preferences = await nlp_service.extract_preferences(user_input, request_id="req-123")

# Refine with additional info
additional = "I'm vegetarian and need wheelchair access"
updated = await nlp_service.refine_preferences(preferences, additional, request_id="req-124")
```

**Conservative Extraction**:
- Only extracts explicitly mentioned information
- Uses `null` for missing data (never guesses)
- Validates against TripPreferences schema (10 required + optional fields)

### `itinerary_service.py` (Implemented)

Generates feasible daily schedules from validated preferences using Gemini LLM.

**Key Class**: `ItineraryService`

**Main Operations**:
1. **Generate Itinerary** - Create multi-day schedules from preferences
2. **Validate Feasibility** - Check budget, time, and transportation constraints

**Example Usage**:
```python
from backend.services.itinerary_service import ItineraryService
from backend.clients.gemini_client import GeminiClient

# Initialize
gemini_client = GeminiClient(api_key=settings.GEMINI_KEY)
itinerary_service = ItineraryService(gemini_client)

# Generate itinerary from validated preferences
preferences_dict = validated_preferences.to_dict()
itinerary = await itinerary_service.generate_itinerary(
    preferences=preferences_dict,
    request_id="req-456"
)

# Access itinerary
for day in itinerary.days:
    print(f"Day {day.day_number}: {day.date}")
    for activity in day.activities:
        print(f"  {activity.planned_start}-{activity.planned_end}: {activity.venue_name} (${activity.estimated_cost})")
    for meal in day.meals:
        print(f"  {meal.meal_type}: {meal.venue_name} (${meal.estimated_cost})")
```

**Key Features**:
- Uses Gemini with `GEMINI_ITINERARY_TEMPERATURE` (0.7) for creative itinerary planning
- Enforces pace-specific parameters from `settings.PACE_PARAMS`
- Validates budget constraints
- Schedules meals at appropriate times
- Accounts for travel time between venues

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

1. **Build Prompt**: Create extraction prompt with JSON schema (10 required + optional fields)
2. **Call Gemini API**: Send prompt with system instruction (primary)
3. **Fallback to Groq**: If Gemini fails, try Groq with `response_format={"type": "json_object"}`
4. **Parse Response**: Extract JSON from LLM response
5. **Create Model**: Convert JSON to `TripPreferences` dataclass
6. **Validate**: Check 10 required fields and business rules

### System Instruction

The NLP service uses this system instruction for both Gemini and Groq:

> "You are a travel planning assistant that extracts structured information from natural language. Extract explicit information mentioned by the user. Infer reasonable defaults only when strongly implied. Use null for truly missing information. Return valid JSON only. Be conservative - only extract what the user clearly communicated."

### JSON Schema

The extraction prompt includes this schema:
```json
{
  "city": "string (default: Kingston)",
  "country": "string (default: Canada)",
  "location_preference": "string or null (e.g., 'downtown', 'waterfront')",
  "starting_location": "string or null",
  "start_date": "string YYYY-MM-DD or null",
  "end_date": "string YYYY-MM-DD or null",
  "duration_days": "number or null",
  "budget": "number or null",
  "budget_currency": "string (default: CAD)",
  "interests": "array of strings",
  "pace": "string (relaxed|moderate|packed) or null",
  "hours_per_day": "number (default: 8) or null",
  "transportation_modes": "array of strings (default: ['mixed'])",
  "group_size": "number or null",
  "group_type": "string or null",
  "dietary_restrictions": "array of strings",
  "accessibility_needs": "array of strings",
  "weather_tolerance": "string or null",
  "must_see_venues": "array of strings",
  "must_avoid_venues": "array of strings"
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
"I want to visit downtown Kingston next weekend"
-> {"city": "Kingston", "location_preference": "downtown", "start_date": "2026-02-13", "end_date": "2026-02-15"}

# Refinement
"Actually make it a 3-day trip and I'm vegetarian"
-> {"...", "end_date": "2026-02-16", "dietary_restrictions": ["vegetarian"]}
```

---

## Itinerary Generation Details

### Generation Process

1. **Validate preferences** - Ensure all 10 required fields present
2. **Build prompt** - Include preferences, pace parameters, and constraints
3. **Call Gemini** - Use `GEMINI_ITINERARY_TEMPERATURE` (0.7) for creative planning
4. **Parse response** - Convert JSON to Itinerary model with Activity, Meal, TravelSegment
5. **Validate feasibility** - Check budget, time, and transportation
6. **Return itinerary** - Complete Itinerary object

### Pace Parameters

Itinerary generation uses `settings.PACE_PARAMS` to enforce pace-specific scheduling:

| Parameter | Relaxed | Moderate | Packed |
|-----------|---------|----------|--------|
| Activities/day | 2-3 | 4-5 | 6-8 |
| Minutes/activity | 90-120 | 60-90 | 30-60 |
| Buffer (min) | 20 | 15 | 5 |
| Lunch (min) | 90 | 75 | 45 |
| Dinner (min) | 120 | 90 | 60 |

---

## Error Handling

### LLM Fallback Flow

```
User Input
    |
    v
Try Gemini (primary)
    |
    +-- Success --> Parse JSON --> Return preferences
    |
    +-- Failure --> Log warning
                    |
                    v
                Try Groq (fallback)
                    |
                    +-- Success --> Parse JSON --> Return preferences
                    |
                    +-- Failure --> Log error --> Raise ExternalAPIError
```

### Common Errors

**Invalid JSON Response**:
```
Error: LLM returned invalid JSON
Cause: LLM didn't return valid JSON
Solution: Retry (usually succeeds on retry)
```

**Network Timeout**:
```
Error: Connection timeout to API
Cause: Network issues or API overload
Solution: Automatic fallback to Groq, then retry with backoff
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

**INFO**: Request start, extraction success, which LLM was used, validation results
```json
{
  "level": "INFO",
  "message": "NLP extraction successful",
  "request_id": "req-123",
  "llm_used": "Gemini",
  "fields_extracted": 12,
  "completeness_score": 0.85
}
```

**WARNING**: Tight budget, fallback to Groq, retries, degraded functionality
```json
{
  "level": "WARNING",
  "message": "Gemini failed, using Groq fallback",
  "request_id": "req-123",
  "gemini_error": "Connection timeout",
  "fallback": "Groq"
}
```

**ERROR**: Both LLMs failed, invalid responses, validation errors
```json
{
  "level": "ERROR",
  "message": "Both Gemini and Groq failed",
  "request_id": "req-123",
  "gemini_error": "Connection timeout",
  "groq_error": "Rate limited"
}
```

### Privacy Protection

User input is **never** logged in full. Only metadata:
```python
# Good
logger.info("Processing user input", extra={
    "request_id": "req-123",
    "input_length": 150,
    "intent": "trip_planning"
})

# Bad - NEVER do this
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

# Itinerary service only
pytest backend/tests/services/test_itinerary_service.py -v

# With coverage
pytest backend/tests/services/ --cov=backend/services --cov-report=html
```

### Test Coverage Requirements

- **NLP Service**: 95% coverage
- **Itinerary Service**: 95% coverage
- **Validation Orchestration**: 100% coverage
- **Error Handling**: 100% coverage

### Key Test Scenarios

#### Extraction Tests
1. Complete input (all fields provided) via Gemini
2. Minimal input (only required fields) via Gemini
3. Budget as total (convert to daily)
4. Budget as daily
5. Multiple interests
6. Dietary restrictions
7. Accessibility needs
8. Transportation modes
9. Pace preference
10. Location preference extraction

#### Fallback Tests
11. Gemini fails, Groq succeeds
12. Both Gemini and Groq fail

#### Refinement Tests
13. Add dietary restriction
14. Update budget
15. Add must-see venues
16. Preserve existing fields

#### Itinerary Tests
17. Generate itinerary with valid preferences
18. Validate feasibility (budget check)
19. Pace parameters applied correctly
20. Meals scheduled at appropriate times

#### Error Handling Tests
21. Empty user input
22. Invalid JSON from API
23. Network timeout (with fallback)
24. Max retries exceeded
25. Invalid extracted data

---

## Performance

### Response Times

**Target**: < 2 seconds for extraction
**Typical**: 500ms - 1.5s (Gemini), 800ms - 1.5s (Groq fallback)

Breakdown:
- Gemini API call: 400-1000ms
- Groq API call (fallback): 600-1200ms
- JSON parsing: 10-50ms
- Validation: 50-100ms
- Logging: 10-20ms

**Itinerary Generation**:
- Gemini API call: 1000-2500ms
- Parsing + validation: 50-200ms

### Optimization Tips

1. **Use Gemini as primary** for faster responses
2. **Use async/await** for concurrent operations
3. **Cache** API responses for identical inputs
4. **Batch** multiple refinements if possible
5. **Reduce temperature** (0.2) for faster, deterministic extraction responses

---

## Integration with Other Modules

### Calls
- `clients.gemini_client.GeminiClient` - Primary LLM API calls
- `clients.groq_client.GroqClient` - Fallback LLM API calls
- `models.trip_preferences.TripPreferences` - Data validation
- `models.itinerary.Itinerary` - Itinerary data structures
- `config.settings` - PACE_PARAMS, temperatures, API config

### Called By
- `controllers.trip_controller` - HTTP request handlers
- `routes.trip_routes` - API endpoints

### Data Flow
```
User Input (HTTP)
    |
    v
routes/trip_routes.py
    |
    v
controllers/trip_controller.py
    |
    v
services/nlp_extraction_service.py
    |
    v
clients/gemini_client.py --> Gemini API (primary)
    |                          |
    | (on failure)             |
    v                          v
clients/groq_client.py --> Groq API (fallback)
    |
    v
models/trip_preferences.py (validation)
    |
    v
services/itinerary_service.py
    |
    v
clients/gemini_client.py --> Gemini API (itinerary)
    |
    v
models/itinerary.py (Itinerary object)
    |
    v
HTTP Response (JSON)
```

---

## Common Issues

### Issue: "Gemini API timeout"

**Cause**: Network latency or API overload

**Solution**:
- Automatic fallback to Groq
- Check Gemini API status
- Verify network connectivity

### Issue: "Invalid JSON from LLM"

**Cause**: LLM returned text instead of JSON

**Solution**:
- Usually resolved by retry or fallback
- Check if system instruction includes "Return valid JSON only"
- Groq supports `response_format={"type": "json_object"}` for guaranteed JSON

### Issue: "Completeness score always low"

**Cause**: User input lacks required information (10 required fields)

**Solution**:
- Guide user with follow-up questions
- Check validation response for missing fields (especially `location_preference`)
- Use refinement to add missing data incrementally

### Issue: "Itinerary exceeds budget"

**Cause**: Generated itinerary costs more than user's budget

**Solution**:
- Check feasibility validation results
- Regenerate with tighter budget constraints
- Suggest increasing budget or reducing activities

---

## Future Enhancements (Phase 2/3)

### Phase 2
- [ ] Implement venue filtering service
- [ ] Implement weather integration service
- [ ] Add caching for API responses
- [ ] Integrate Google Maps for travel time estimation

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

### When Using Itinerary Service

1. **Validate preferences first** (all 10 required fields)
2. **Check feasibility** after generation
3. **Handle budget overruns** gracefully
4. **Log generation metrics** (days, activities, budget used)

### Prompt Engineering

1. **Be specific** in extraction schema (10 required + optional fields)
2. **Include examples** in system instruction if needed
3. **Use low temperature** (0.2) for extraction, higher (0.7) for itinerary
4. **Use JSON mode** when available (Groq `response_format`)

---

## API Reference

### `NLPExtractionService`

**Constructor**:
```python
NLPExtractionService(
    gemini_client: GeminiClient,
    groq_client: Optional[GroqClient] = None
)
```

**Methods**:

**`async extract_preferences(user_input: str, request_id: str) -> TripPreferences`**

Extracts trip preferences from natural language. Tries Gemini first, falls back to Groq.

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

### `ItineraryService`

**Constructor**:
```python
ItineraryService(gemini_client: GeminiClient)
```

**Methods**:

**`async generate_itinerary(preferences: Dict, request_id: str) -> Itinerary`**

Generates a multi-day itinerary from validated preferences.

- **Args**:
  - `preferences`: Validated TripPreferences as dict
  - `request_id`: UUID for correlation
- **Returns**: `Itinerary` object
- **Raises**: `ExternalAPIError`

**`async validate_feasibility(itinerary: Itinerary, request_id: str) -> Dict[str, Any]`**

Validates itinerary feasibility (budget, time, transportation).

- **Args**:
  - `itinerary`: Generated itinerary
  - `request_id`: UUID for correlation
- **Returns**: `{"valid": bool, "issues": [...], "warnings": [...]}`

---

## Contributing

When adding new services:

1. **Follow naming convention**: `<domain>_service.py`
2. **Add comprehensive tests** (95%+ coverage)
3. **Document in CLAUDE.md** (agent instructions)
4. **Document in README.md** (human guide)
5. **Add logging** with request correlation
6. **Handle errors** with LLM fallback where appropriate

---

**Last Updated**: 2026-02-07
**Maintained By**: Backend Team
**Questions**: See `backend/services/CLAUDE.md` for detailed agent instructions
