# Services Module - Agent Instructions

**Parent Contexts**:
- `MONVOYAGE/CLAUDE.md` (project-wide architecture, testing conventions)
- `MONVOYAGE/backend/CLAUDE_EMBEDDED.md` (backend-operational rules, MVP requirements)

**Module Purpose**: Business logic layer containing trip planning services - NLP extraction, itinerary generation, budget tracking, and schedule adaptation.

---

## Module Responsibilities

### Current (Phase 1)
1. **NLP Extraction** (`nlp_extraction_service.py`) - Extract structured TripPreferences from natural language user input using Gemini (primary) or Groq (fallback)
2. Preference refinement (updating existing preferences with new input)
3. Validation orchestration (call model validation, handle results)
4. **Itinerary Generation** (`itinerary_service.py`) - Generate feasible daily schedules from validated preferences using Gemini

### Planned (Phase 2/3)
5. **Budget Tracking** (`budget_service.py`) - Real-time spending monitor with overspend alerts
6. **Schedule Adaptation** (`adaptation_service.py`) - Re-optimize itinerary when users run late/skip activities
7. **Weather Integration** (`weather_service.py`) - Fetch forecasts and warn about outdoor activities
8. **Venue Filtering** (`venue_service.py`) - Filter Kingston venues by interests, budget, accessibility

---

## Files in This Module

### `nlp_extraction_service.py` (Phase 1 - Current)

**Purpose**: Extract structured trip preferences from natural language using Gemini (primary) or Groq (fallback) LLM.

**Key Functions**:
```python
class NLPExtractionService:
    """Natural language extraction for trip preferences"""

    def __init__(self, gemini_client: GeminiClient, groq_client: Optional[GroqClient] = None):
        self.gemini_client = gemini_client
        self.groq_client = groq_client  # Optional fallback
        self.logger = logging.getLogger(__name__)

    async def extract_preferences(
        self,
        user_input: str,
        request_id: str
    ) -> TripPreferences:
        """
        Extract trip preferences from natural language.

        Uses Gemini as primary LLM, falls back to Groq if Gemini fails.

        Args:
            user_input: Raw user message (e.g., "I want to visit Kingston March 15-17...")
            request_id: UUID for request correlation

        Returns:
            TripPreferences object with extracted data

        Raises:
            ExternalAPIError: If both Gemini and Groq APIs fail
            ValidationError: If extracted data invalid
        """
        self.logger.info("Starting NLP extraction", extra={
            "request_id": request_id,
            "input_length": len(user_input)
        })

        try:
            # Try Gemini first (primary)
            prompt = self._build_extraction_prompt(user_input)
            response_text = await self.gemini_client.generate_content(
                prompt=prompt,
                system_instruction=self._get_system_instruction(),
                temperature=settings.GEMINI_EXTRACTION_TEMPERATURE,
                max_tokens=settings.GEMINI_EXTRACTION_MAX_TOKENS,
                request_id=request_id
            )

            # Parse JSON response
            extracted_data = json.loads(response_text)

            # Create TripPreferences
            preferences = TripPreferences.from_dict(extracted_data)

            self.logger.info("NLP extraction successful (Gemini)", extra={
                "request_id": request_id,
                "fields_extracted": len([v for v in extracted_data.values() if v])
            })

            return preferences

        except Exception as gemini_error:
            self.logger.warning("Gemini extraction failed, trying Groq fallback", extra={
                "request_id": request_id,
                "gemini_error": str(gemini_error)
            })

            if not self.groq_client:
                raise

            # Fall back to Groq
            try:
                response = await self.groq_client.chat_completion(
                    messages=[
                        {"role": "system", "content": self._get_system_instruction()},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=settings.GROQ_TEMPERATURE,
                    max_tokens=settings.GROQ_MAX_TOKENS,
                    request_id=request_id
                )

                extracted_data = json.loads(response["choices"][0]["message"]["content"])
                preferences = TripPreferences.from_dict(extracted_data)

                self.logger.info("NLP extraction successful (Groq fallback)", extra={
                    "request_id": request_id,
                    "fields_extracted": len([v for v in extracted_data.values() if v])
                })

                return preferences

            except Exception as groq_error:
                self.logger.error("Both Gemini and Groq extraction failed", extra={
                    "request_id": request_id,
                    "gemini_error": str(gemini_error),
                    "groq_error": str(groq_error)
                }, exc_info=True)
                raise

    async def refine_preferences(
        self,
        existing_preferences: TripPreferences,
        additional_input: str,
        request_id: str
    ) -> TripPreferences:
        """
        Update existing preferences with new information.

        Args:
            existing_preferences: Previously extracted preferences
            additional_input: New user input (e.g., "I'm vegetarian")
            request_id: UUID for request correlation

        Returns:
            Updated TripPreferences
        """
        self.logger.info("Refining preferences", extra={
            "request_id": request_id,
            "trip_id": existing_preferences.trip_id
        })

        try:
            # Build refinement prompt with existing data
            prompt = self._build_refinement_prompt(
                existing_preferences.to_dict(),
                additional_input
            )

            # Try Gemini first
            response_text = await self.gemini_client.generate_content(
                prompt=prompt,
                system_instruction=self._get_system_instruction(),
                temperature=settings.GEMINI_EXTRACTION_TEMPERATURE,
                max_tokens=settings.GEMINI_EXTRACTION_MAX_TOKENS,
                request_id=request_id
            )

            # Parse and merge with existing
            updated_data = json.loads(response_text)
            updated_preferences = TripPreferences.from_dict(updated_data)

            # Preserve trip_id and timestamps
            updated_preferences.trip_id = existing_preferences.trip_id
            updated_preferences.created_at = existing_preferences.created_at

            self.logger.info("Preferences refined (Gemini)", extra={
                "request_id": request_id,
                "trip_id": updated_preferences.trip_id
            })

            return updated_preferences

        except Exception as e:
            self.logger.error("Preference refinement failed", extra={
                "request_id": request_id
            }, exc_info=True)
            raise

    def _build_extraction_prompt(self, user_input: str) -> str:
        """Build extraction prompt with JSON schema"""
        schema = {
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

        return f"""Extract travel preferences from this user message:

User message: "{user_input}"

Return a JSON object with this structure:
{json.dumps(schema, indent=2)}

Rules:
- Only include information explicitly mentioned or strongly implied
- Use null for missing information
- Return empty arrays [] if no items mentioned
- For dates, use YYYY-MM-DD format
- For interests, use: history, food, waterfront, nature, arts, museums, shopping, nightlife
- For transportation, use: "own car", "rental car", "Kingston Transit", "walking only", "mixed"
- For pace, ONLY use: "relaxed", "moderate", or "packed"
- For location_preference, extract area like "downtown", "waterfront", "near nature"
- Return ONLY valid JSON, no explanation

JSON response:"""

    def _build_refinement_prompt(
        self,
        existing_data: dict,
        additional_input: str
    ) -> str:
        """Build refinement prompt with existing data"""
        return f"""You previously extracted these preferences:

{json.dumps(existing_data, indent=2)}

The user now provides additional information:
"{additional_input}"

Update the JSON with the new information.
Keep existing values unless the new information contradicts or updates them.
Return the complete updated JSON object.

JSON response:"""

    def _get_system_instruction(self) -> str:
        """System instruction for LLM API"""
        return """You are a travel planning assistant that extracts structured information from natural language.

Your task is to:
1. Extract explicit information mentioned by the user
2. Infer reasonable defaults only when strongly implied
3. Use null for truly missing information
4. Return valid JSON only

Be conservative - only extract what the user clearly communicated."""
```

---

### `itinerary_service.py` (Implemented)

**Purpose**: Generate feasible multi-day itineraries from validated preferences using Gemini LLM.

**Key Functions**:
```python
class ItineraryService:
    """Itinerary generation and feasibility validation"""

    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client
        self.logger = logging.getLogger(__name__)

    async def generate_itinerary(
        self,
        preferences: Dict,
        request_id: str
    ) -> Itinerary:
        """
        Generate itinerary from validated preferences.

        Uses Gemini with GEMINI_ITINERARY_TEMPERATURE and GEMINI_ITINERARY_MAX_TOKENS.

        Args:
            preferences: Validated TripPreferences as dict
            request_id: UUID for request correlation

        Returns:
            Itinerary object with daily schedules

        Must enforce:
        - Pace-specific parameters (from settings.PACE_PARAMS)
        - Budget constraints (total and daily)
        - Time constraints (hours_per_day, venue hours)
        - Transportation feasibility (travel times)
        - Weather warnings (outdoor activities)
        """
        self.logger.info("Generating itinerary", extra={
            "request_id": request_id,
            "pace": preferences.get("pace"),
            "duration_days": preferences.get("duration_days"),
            "budget": preferences.get("budget")
        })

        prompt = self._build_itinerary_prompt(preferences)

        response_text = await self.gemini_client.generate_content(
            prompt=prompt,
            system_instruction=GEMINI_ITINERARY_SYSTEM_INSTRUCTION,
            temperature=settings.GEMINI_ITINERARY_TEMPERATURE,
            max_tokens=settings.GEMINI_ITINERARY_MAX_TOKENS,
            request_id=request_id
        )

        # Parse response into Itinerary model
        itinerary_data = json.loads(response_text)
        itinerary = self._build_itinerary(itinerary_data, preferences)

        # Validate feasibility
        validation = await self.validate_feasibility(itinerary, request_id)
        if not validation["valid"]:
            self.logger.warning("Itinerary feasibility issues", extra={
                "request_id": request_id,
                "issues": validation["issues"]
            })

        self.logger.info("Itinerary generated", extra={
            "request_id": request_id,
            "days": len(itinerary.days),
            "total_activities": sum(len(d.activities) for d in itinerary.days)
        })

        return itinerary

    async def validate_feasibility(
        self,
        itinerary: Itinerary,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Validate itinerary is feasible.

        Checks:
        - Total time fits in available hours
        - Budget not exceeded
        - Venues open during planned times
        - Travel times realistic
        - Meals scheduled appropriately
        """
        return itinerary.validate()

    def _build_itinerary_prompt(self, preferences: Dict) -> str:
        """Build itinerary generation prompt from preferences"""
        pace_params = settings.PACE_PARAMS.get(preferences.get("pace", "moderate"), {})

        return f"""Generate a detailed {preferences.get('duration_days', 1)}-day itinerary for Kingston, Ontario.

User Preferences:
- Location: {preferences.get('location_preference', 'downtown')}
- Dates: {preferences.get('start_date')} to {preferences.get('end_date')}
- Budget: ${preferences.get('budget', 200)} {preferences.get('budget_currency', 'CAD')} total
- Interests: {', '.join(preferences.get('interests', []))}
- Pace: {preferences.get('pace', 'moderate')}
- Hours per day: {preferences.get('hours_per_day', 8)}
- Transportation: {', '.join(preferences.get('transportation_modes', ['mixed']))}

Pace constraints:
- Activities per day: {pace_params.get('activities_per_day', (4, 5))}
- Minutes per activity: {pace_params.get('minutes_per_activity', (60, 90))}
- Buffer between activities: {pace_params.get('buffer_minutes', 15)} min
- Lunch duration: {pace_params.get('lunch_minutes', 75)} min
- Dinner duration: {pace_params.get('dinner_minutes', 90)} min

Return a JSON itinerary with days, activities, meals, and travel segments."""
```

**GEMINI_ITINERARY_SYSTEM_INSTRUCTION** (referenced by ItineraryService):
```python
GEMINI_ITINERARY_SYSTEM_INSTRUCTION = """You are an itinerary planning engine for Kingston, Ontario, Canada.

Generate feasible, time-aware daily itineraries that:
1. Respect pace parameters (activities/day, duration, buffers)
2. Stay within budget constraints
3. Include meals at appropriate times
4. Account for travel time between venues
5. Consider weather for outdoor activities
6. Respect venue opening hours

Return valid JSON with this structure for each day:
- day_number, date
- activities: [{venue_name, planned_start, planned_end, estimated_cost}]
- meals: [{meal_type, venue_name, planned_start, planned_end, estimated_cost}]
- travel_segments: [{from_venue, to_venue, mode, estimated_duration_minutes}]"""
```

---

## Non-Negotiable Rules

### NLP Extraction Rules
1. **Conservative Extraction**: Only extract explicitly mentioned or strongly implied information
2. **No Hallucination**: Use `null` for missing data, never guess
3. **Valid JSON Only**: Response must parse as valid JSON
4. **Schema Adherence**: All fields must match TripPreferences schema (10 required + optional)
5. **Gemini First**: Always try Gemini before falling back to Groq

### Itinerary Generation Rules
1. **Validate preferences** before generating (all 10 required fields present)
2. **Respect pace parameters** from settings.PACE_PARAMS
3. **Stay within budget** (total and daily)
4. **Schedule meals** at appropriate times (lunch 11:30-13:30, dinner 17:30-20:00)
5. **Account for travel time** between venues

### Validation Orchestration
1. **ALWAYS** validate extracted preferences before returning
2. **LOG** validation issues at WARNING level (non-blocking) and ERROR level (blocking)
3. **RETURN** validation results with preferences
4. **NEVER** proceed with invalid preferences (< $50/day, missing required fields)

### Error Handling
1. **Try Gemini first**, fall back to Groq on failure
2. **Retry** API failures up to 3 times with exponential backoff
3. **LOG** full error traceback on failures
4. **Redact** user input in logs (only log intent/summary, not full message)
5. **Propagate** errors with clear messages

---

## Logging Requirements

### What to Log
- **INFO**: Extraction start/success, validation results, completeness scores, which LLM was used
- **DEBUG**: Prompts sent to API (redacted), API responses (redacted), parsing steps
- **WARNING**: Validation warnings, retry attempts, fallback to Groq, degraded functionality
- **ERROR**: API failures, invalid JSON, validation errors, both LLMs failed
- **CRITICAL**: Repeated API failures, service unavailable

### Log Examples
```python
# NLP extraction start
logger.info("Starting NLP extraction", extra={
    "request_id": request_id,
    "input_length": len(user_input),
    "service": "nlp_extraction",
    "primary_llm": "Gemini"
})

# Extraction success
logger.info("NLP extraction successful", extra={
    "request_id": request_id,
    "llm_used": "Gemini",
    "fields_extracted": 12,
    "completeness_score": 0.85
})

# Fallback to Groq
logger.warning("Gemini extraction failed, falling back to Groq", extra={
    "request_id": request_id,
    "gemini_error": "Connection timeout",
    "fallback": "Groq"
})

# Itinerary generation
logger.info("Itinerary generated", extra={
    "request_id": request_id,
    "llm_used": "Gemini",
    "days": 3,
    "total_activities": 12,
    "total_budget_used": 180.0
})

# API error with retry
logger.error("Both LLMs failed for extraction", extra={
    "request_id": request_id,
    "gemini_error": "Connection timeout",
    "groq_error": "Rate limited"
}, exc_info=True)
```

### Secrets Redaction
```python
# NEVER log full user input (may contain PII)
logger.debug("User input summary", extra={
    "request_id": request_id,
    "intent": "trip_planning",
    "input_length": len(user_input)
    # DO NOT: "user_input": user_input
})
```

---

## Testing Strategy

### Unit Tests Required (Minimum 20)

**NLP Extraction Tests**:
1. Test extraction with complete user input (all fields)
2. Test extraction with minimal user input (only required fields)
3. Test extraction with budget as total (calculate daily)
4. Test extraction with budget as daily
5. Test extraction with interests list
6. Test extraction with pace preference
7. Test extraction with transportation modes
8. Test extraction with dietary restrictions
9. Test extraction with accessibility needs
10. Test extraction with location_preference
11. Test refinement (add dietary restriction to existing preferences)
12. Test refinement (update budget in existing preferences)
13. Test refinement (preserve existing fields not mentioned)
14. Test prompt building (extraction) with new schema fields
15. Test prompt building (refinement)
16. Test system instruction content
17. Test Gemini to Groq fallback on failure

**Itinerary Generation Tests**:
18. Test itinerary generation with valid preferences
19. Test itinerary feasibility validation (budget check)
20. Test itinerary prompt includes pace parameters

### Integration Tests Required (Minimum 5)
1. Test with real Gemini API (using test API key)
2. Test with real Groq API fallback
3. Test with network timeout (must retry/fallback)
4. Test with invalid JSON response from API
5. Test end-to-end extraction -> validation -> itinerary pipeline

### Negative Tests Required (Minimum 5)
1. Test with empty user input (must handle gracefully)
2. Test with Gemini API returning non-JSON
3. Test with both Gemini and Groq failing
4. Test with invalid extracted data (e.g., budget as string)
5. Test itinerary generation with invalid preferences (must reject)

### Test Examples
```python
@pytest.mark.asyncio
async def test_extract_preferences_gemini_primary(mock_gemini_client):
    """Test extraction using Gemini (primary)"""
    service = NLPExtractionService(mock_gemini_client)

    user_input = """I want to visit downtown Kingston from March 15-17, 2026.
    My budget is $200. I'm interested in history and food.
    I have my own car and want a moderate pace."""

    # Mock Gemini response
    mock_gemini_client.generate_content.return_value = json.dumps({
        "city": "Kingston",
        "country": "Canada",
        "location_preference": "downtown",
        "start_date": "2026-03-15",
        "end_date": "2026-03-17",
        "budget": 200.0,
        "interests": ["history", "food"],
        "transportation_modes": ["own car"],
        "pace": "moderate"
    })

    preferences = await service.extract_preferences(user_input, "req-123")

    assert preferences.city == "Kingston"
    assert preferences.location_preference == "downtown"
    assert preferences.start_date == "2026-03-15"
    assert preferences.budget == 200.0
    assert "history" in preferences.interests
    assert preferences.pace == "moderate"

@pytest.mark.asyncio
async def test_extract_preferences_groq_fallback(mock_gemini_client, mock_groq_client):
    """Test fallback to Groq when Gemini fails"""
    mock_gemini_client.generate_content.side_effect = ExternalAPIError("Gemini", "timeout")

    service = NLPExtractionService(mock_gemini_client, mock_groq_client)

    mock_groq_client.chat_completion.return_value = {
        "choices": [{"message": {"content": json.dumps({
            "city": "Kingston",
            "location_preference": "downtown",
            "start_date": "2026-03-15",
            "end_date": "2026-03-17",
            "budget": 200.0,
            "interests": ["history"],
            "pace": "moderate"
        })}}]
    }

    preferences = await service.extract_preferences("Visit Kingston...", "req-123")

    assert preferences.start_date == "2026-03-15"
    mock_groq_client.chat_completion.assert_called_once()

@pytest.mark.asyncio
async def test_generate_itinerary(mock_gemini_client):
    """Test itinerary generation"""
    service = ItineraryService(mock_gemini_client)

    preferences = {
        "city": "Kingston",
        "location_preference": "downtown",
        "start_date": "2026-03-15",
        "end_date": "2026-03-17",
        "duration_days": 3,
        "budget": 200.0,
        "interests": ["history", "food"],
        "pace": "moderate",
        "hours_per_day": 8,
        "transportation_modes": ["mixed"]
    }

    mock_gemini_client.generate_content.return_value = json.dumps({
        "days": [
            {
                "day_number": 1,
                "date": "2026-03-15",
                "activities": [{"venue_name": "Fort Henry", "planned_start": "09:00", "planned_end": "11:00", "estimated_cost": 25.0}],
                "meals": [{"meal_type": "lunch", "venue_name": "Chez Piggy", "estimated_cost": 30.0}]
            }
        ]
    })

    itinerary = await service.generate_itinerary(preferences, "req-456")

    assert len(itinerary.days) > 0
```

---

## Error Handling

### External API Errors
```python
class ExternalAPIError(Exception):
    """Raised when external API fails"""
    def __init__(self, service: str, error: str, retry_count: int = 0):
        self.service = service
        self.error = error
        self.retry_count = retry_count

# Usage with Gemini -> Groq fallback
async def extract_with_fallback(user_input: str, request_id: str) -> TripPreferences:
    try:
        # Try Gemini (primary)
        return await extract_via_gemini(user_input, request_id)
    except ExternalAPIError:
        logger.warning("Gemini failed, falling back to Groq")
        try:
            # Try Groq (fallback)
            return await extract_via_groq(user_input, request_id)
        except ExternalAPIError:
            logger.error("Both Gemini and Groq failed")
            raise
```

---

## Integration Points

### Used By
- `controllers/trip_controller.py` - Calls NLP extraction and itinerary generation
- `routes/trip_routes.py` - HTTP handlers for extraction and itinerary endpoints

### Uses
- `clients/gemini_client.py` - Primary LLM API wrapper
- `clients/groq_client.py` - Fallback LLM API wrapper
- `models/trip_preferences.py` - Data structures and validation
- `models/itinerary.py` - Itinerary data structures
- `config/settings.py` - API configuration, PACE_PARAMS, temperatures

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

## Assumptions
1. Gemini API is always tried first; Groq is optional fallback
2. User input is in English
3. All dates refer to current year or future
4. Kingston, Ontario is the only city supported

## Open Questions
1. Should extraction support multiple languages?
2. How to handle ambiguous date references ("next weekend")?
3. Should we cache extraction results to avoid re-processing?
4. What is the maximum user input length to accept?
5. Should itinerary generation retry with different prompts on failure?

---

**Last Updated**: 2026-02-07
**Status**: Phase 1 - NLPExtractionService (Gemini primary, Groq fallback) and ItineraryService implemented
