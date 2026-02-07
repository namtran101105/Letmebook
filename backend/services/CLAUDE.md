# Services Module - Agent Instructions

**Parent Contexts**:
- `MONVOYAGE/CLAUDE.md` (project-wide architecture, testing conventions)
- `MONVOYAGE/backend/CLAUDE_EMBEDDED.md` (backend-operational rules, MVP requirements)

**Module Purpose**: Business logic layer containing trip planning services - NLP extraction, itinerary generation, budget tracking, and schedule adaptation.

---

## Module Responsibilities

### Current (Phase 1)
1. **NLP Extraction** (`nlp_extraction_service.py`) - Extract structured TripPreferences from natural language user input using Groq API
2. Preference refinement (updating existing preferences with new input)
3. Validation orchestration (call model validation, handle results)

### Planned (Phase 2/3)
4. **Itinerary Generation** (`itinerary_service.py`) - Generate feasible daily schedules from validated preferences
5. **Budget Tracking** (`budget_service.py`) - Real-time spending monitor with overspend alerts
6. **Schedule Adaptation** (`adaptation_service.py`) - Re-optimize itinerary when users run late/skip activities
7. **Weather Integration** (`weather_service.py`) - Fetch forecasts and warn about outdoor activities
8. **Venue Filtering** (`venue_service.py`) - Filter Kingston venues by interests, budget, accessibility

---

## Files in This Module

### `nlp_extraction_service.py` (Phase 1 - Current)

**Purpose**: Extract structured trip preferences from natural language using Groq LLM.

**Key Functions**:
```python
class NLPExtractionService:
    """Natural language extraction for trip preferences"""
    
    def __init__(self, groq_client: GroqClient):
        self.groq_client = groq_client
        self.logger = logging.getLogger(__name__)
    
    async def extract_preferences(
        self, 
        user_input: str,
        request_id: str
    ) -> TripPreferences:
        """
        Extract trip preferences from natural language.
        
        Args:
            user_input: Raw user message (e.g., "I want to visit Kingston March 15-17...")
            request_id: UUID for request correlation
        
        Returns:
            TripPreferences object with extracted data
        
        Raises:
            ExternalAPIError: If Groq API fails
            ValidationError: If extracted data invalid
        """
        self.logger.info("Starting NLP extraction", extra={
            "request_id": request_id,
            "input_length": len(user_input)
        })
        
        try:
            # Build extraction prompt
            prompt = self._build_extraction_prompt(user_input)
            
            # Call Groq API with JSON mode
            response = await self.groq_client.chat_completion(
                messages=[
                    {"role": "system", "content": self._get_system_instruction()},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=2048
            )
            
            # Parse JSON response
            extracted_data = json.loads(response.choices[0].message.content)
            
            # Create TripPreferences
            preferences = TripPreferences.from_dict(extracted_data)
            
            self.logger.info("NLP extraction successful", extra={
                "request_id": request_id,
                "fields_extracted": len([v for v in extracted_data.values() if v])
            })
            
            return preferences
            
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON from Groq", extra={
                "request_id": request_id,
                "error": str(e)
            }, exc_info=True)
            raise ExternalAPIError("Groq", "Invalid JSON response")
            
        except Exception as e:
            self.logger.error("NLP extraction failed", extra={
                "request_id": request_id,
                "error_type": type(e).__name__
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
            
            response = await self.groq_client.chat_completion(
                messages=[
                    {"role": "system", "content": self._get_system_instruction()},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=2048
            )
            
            # Parse and merge with existing
            updated_data = json.loads(response.choices[0].message.content)
            updated_preferences = TripPreferences.from_dict(updated_data)
            
            # Preserve trip_id and timestamps
            updated_preferences.trip_id = existing_preferences.trip_id
            updated_preferences.created_at = existing_preferences.created_at
            
            self.logger.info("Preferences refined", extra={
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
            "starting_location": "string or null",
            "city": "string (default: Kingston)",
            "country": "string (default: Canada)",
            "start_date": "string YYYY-MM-DD or null",
            "end_date": "string YYYY-MM-DD or null",
            "budget": "number or null",
            "interests": "array of strings",
            "hours_per_day": "number or null",
            "transportation_modes": "array of strings",
            "pace": "string (relaxed|moderate|packed) or null",
            "group_size": "number or null",
            "group_type": "string or null",
            "dietary_restrictions": "array of strings",
            "accessibility_needs": "array of strings",
            "weather_tolerance": "string or null",
            "must_see_venues": "array of strings",
            "location_preference": "string or null"
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
        """System instruction for Groq API"""
        return """You are a travel planning assistant that extracts structured information from natural language.

Your task is to:
1. Extract explicit information mentioned by the user
2. Infer reasonable defaults only when strongly implied
3. Use null for truly missing information
4. Return valid JSON only

Be conservative - only extract what the user clearly communicated."""
```

---

### `itinerary_service.py` (Phase 2 - Planned)

**Purpose**: Generate feasible multi-day itineraries from validated preferences.

**Key Functions**:
```python
class ItineraryService:
    """Itinerary generation and feasibility validation"""
    
    async def generate_itinerary(
        self,
        preferences: TripPreferences,
        venues: List[Venue],
        request_id: str
    ) -> Itinerary:
        """
        Generate itinerary from preferences.
        
        Must enforce:
        - Pace-specific parameters (from CLAUDE_EMBEDDED.md)
        - Budget constraints (total and daily)
        - Time constraints (hours_per_day, venue hours)
        - Transportation feasibility (travel times)
        - Weather warnings (outdoor activities)
        """
        pass
    
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
        pass
```

---

## Non-Negotiable Rules

### NLP Extraction Rules
1. **Conservative Extraction**: Only extract explicitly mentioned or strongly implied information
2. **No Hallucination**: Use `null` for missing data, never guess
3. **Valid JSON Only**: Response must parse as valid JSON
4. **Schema Adherence**: All fields must match TripPreferences schema

### Validation Orchestration
1. **ALWAYS** validate extracted preferences before returning
2. **LOG** validation issues at WARNING level (non-blocking) and ERROR level (blocking)
3. **RETURN** validation results with preferences
4. **NEVER** proceed with invalid preferences (< $50/day, missing required fields)

### Error Handling
1. **Retry** Groq API failures up to 3 times with exponential backoff
2. **LOG** full error traceback on failures
3. **Redact** user input in logs (only log intent/summary, not full message)
4. **Propagate** errors with clear messages

---

## Logging Requirements

### What to Log
- **INFO**: Extraction start/success, validation results, completeness scores
- **DEBUG**: Prompts sent to API (redacted), API responses (redacted), parsing steps
- **WARNING**: Validation warnings, retry attempts, degraded functionality
- **ERROR**: API failures, invalid JSON, validation errors
- **CRITICAL**: Repeated API failures, service unavailable

### Log Examples
```python
# NLP extraction start
logger.info("Starting NLP extraction", extra={
    "request_id": request_id,
    "input_length": len(user_input),
    "service": "nlp_extraction"
})

# Extraction success
logger.info("NLP extraction successful", extra={
    "request_id": request_id,
    "fields_extracted": 12,
    "completeness_score": 0.85
})

# Validation warning
logger.warning("Budget is tight", extra={
    "request_id": request_id,
    "daily_budget": 55.0,
    "minimum": 50.0,
    "impact": "Will prioritize affordable options"
})

# API error with retry
logger.error("Groq API failed, retrying", extra={
    "request_id": request_id,
    "retry_count": 1,
    "error": "Connection timeout"
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

# Redact API keys in logs
logger.debug("Calling Groq API", extra={
    "api_key": redact_api_key(api_key),
    "model": "llama-3.3-70b-versatile"
})
```

---

## Testing Strategy

### Unit Tests Required (Minimum 15)
1. Test extraction with complete user input (all fields)
2. Test extraction with minimal user input (only required fields)
3. Test extraction with budget as total (calculate daily)
4. Test extraction with budget as daily
5. Test extraction with interests list
6. Test extraction with pace preference
7. Test extraction with transportation modes
8. Test extraction with dietary restrictions
9. Test extraction with accessibility needs
10. Test refinement (add dietary restriction to existing preferences)
11. Test refinement (update budget in existing preferences)
12. Test refinement (preserve existing fields not mentioned)
13. Test prompt building (extraction)
14. Test prompt building (refinement)
15. Test system instruction content

### Integration Tests Required (Minimum 5)
1. Test with real Groq API (using test API key)
2. Test with invalid Groq API key (must fail gracefully)
3. Test with network timeout (must retry)
4. Test with invalid JSON response from API
5. Test end-to-end extraction → validation pipeline

### Negative Tests Required (Minimum 5)
1. Test with empty user input (must handle gracefully)
2. Test with Groq API returning non-JSON
3. Test with Groq API returning malformed JSON
4. Test with network failure (no retries left)
5. Test with invalid extracted data (e.g., budget as string)

### Test Examples
```python
@pytest.mark.asyncio
async def test_extract_preferences_complete_input(mock_groq_client):
    """Test extraction with all fields provided"""
    service = NLPExtractionService(mock_groq_client)
    
    user_input = """I want to visit Kingston from March 15-17, 2026. 
    My budget is $200. I'm interested in history and food. 
    I have my own car and want a moderate pace. 
    I'm vegetarian and need wheelchair access."""
    
    # Mock Groq response
    mock_groq_client.chat_completion.return_value = MockResponse(
        content=json.dumps({
            "starting_location": null,
            "city": "Kingston",
            "start_date": "2026-03-15",
            "end_date": "2026-03-17",
            "budget": 200.0,
            "interests": ["history", "food"],
            "transportation_modes": ["own car"],
            "pace": "moderate",
            "dietary_restrictions": ["vegetarian"],
            "accessibility_needs": ["wheelchair access"]
        })
    )
    
    preferences = await service.extract_preferences(user_input, "req-123")
    
    assert preferences.start_date == "2026-03-15"
    assert preferences.budget == 200.0
    assert "history" in preferences.interests
    assert preferences.pace == "moderate"
    assert "vegetarian" in preferences.dietary_restrictions

@pytest.mark.asyncio
async def test_refine_preferences_add_dietary(mock_groq_client):
    """Test refining existing preferences with dietary restriction"""
    service = NLPExtractionService(mock_groq_client)
    
    existing = TripPreferences(
        start_date="2026-03-15",
        end_date="2026-03-17",
        budget=200.0,
        interests=["history"],
        pace="moderate"
    )
    
    additional_input = "I'm vegetarian and want to see Fort Henry"
    
    # Mock Groq response with updated data
    mock_groq_client.chat_completion.return_value = MockResponse(
        content=json.dumps({
            **existing.to_dict(),
            "dietary_restrictions": ["vegetarian"],
            "must_see_venues": ["Fort Henry"]
        })
    )
    
    updated = await service.refine_preferences(
        existing, additional_input, "req-123"
    )
    
    assert updated.start_date == existing.start_date  # Preserved
    assert "vegetarian" in updated.dietary_restrictions  # Added
    assert "Fort Henry" in updated.must_see_venues  # Added
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

# Usage with retry logic
async def extract_with_retry(user_input: str) -> TripPreferences:
    max_retries = 3
    backoff = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            return await extract_preferences(user_input, request_id)
        except ExternalAPIError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Retry {attempt+1}/{max_retries}", extra={
                    "service": e.service,
                    "error": e.error
                })
                await asyncio.sleep(backoff * (2 ** attempt))
            else:
                logger.error("Max retries exceeded", exc_info=True)
                raise
```

---

## Integration Points

### Used By
- `controllers/trip_controller.py` - Calls NLP extraction for user input
- `routes/trip_routes.py` - HTTP handlers for extraction endpoints

### Uses
- `clients/groq_client.py` - Groq API wrapper
- `models/trip_preferences.py` - Data structures and validation
- `config/settings.py` - API configuration

---

## Assumptions
1. Groq API response is always valid JSON when `response_format={"type": "json_object"}` is set
2. User input is in English
3. All dates refer to current year or future
4. Kingston, Ontario is the only city supported

## Open Questions
1. Should extraction support multiple languages?
2. How to handle ambiguous date references ("next weekend")?
3. Should we cache extraction results to avoid re-processing?
4. What is the maximum user input length to accept?

---

**Last Updated**: 2026-02-07  
**Status**: Phase 1 - Documentation Complete, Implementation Pending
