# Controllers Module - Agent Instructions

**Parent Contexts**:
- `MONVOYAGE/CLAUDE.md` (project-wide architecture, testing conventions)
- `MONVOYAGE/backend/CLAUDE_EMBEDDED.md` (backend-operational rules, MVP requirements)

**Module Purpose**: Request handlers that orchestrate business logic. Controllers sit between routes (HTTP layer) and services (business logic), coordinating operations and formatting responses.

---

## Module Responsibilities

### Current (Phase 1)
1. **Trip Controller** (`trip_controller.py`) - Handle trip preference extraction and refinement requests
2. Orchestrate NLP service calls
3. Validate results
4. Format responses for routes

### Planned (Phase 2/3)
5. **Itinerary Controller** - Handle itinerary generation and management
6. **Budget Controller** - Handle budget tracking operations
7. **Venue Controller** - Handle venue search and filtering
8. Request/response transformation
9. Business logic orchestration

---

## Files in This Module

### `trip_controller.py` (Phase 1 - Current)

**Purpose**: Handle trip preference operations, orchestrating NLP extraction and validation.

**Must Include**:
```python
import logging
from typing import Dict, Any
from backend.services.nlp_extraction_service import NLPExtractionService
from backend.clients.groq_client import GroqClient
from backend.models.trip_preferences import TripPreferences
from backend.config.settings import settings

class TripController:
    """Controller for trip preference operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.groq_client = GroqClient(api_key=settings.GROQ_API_KEY)
        self.nlp_service = NLPExtractionService(self.groq_client)
    
    async def extract_preferences(
        self,
        user_input: str,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Extract trip preferences from user input.
        
        Args:
            user_input: Natural language trip description
            request_id: UUID for correlation logging
        
        Returns:
            Dict with:
            - preferences: TripPreferences as dict
            - validation: Validation results
        
        Raises:
            ValidationError: If validation fails
            ExternalAPIError: If NLP service fails
        """
        self.logger.info("Extracting preferences", extra={
            "request_id": request_id,
            "controller": "trip"
        })
        
        # Call NLP service
        preferences = await self.nlp_service.extract_preferences(
            user_input=user_input,
            request_id=request_id
        )
        
        # Validate preferences
        validation = preferences.validate()
        
        self.logger.info("Preferences extracted", extra={
            "request_id": request_id,
            "valid": validation["valid"],
            "completeness": validation["completeness_score"]
        })
        
        # Return formatted response
        return {
            "preferences": preferences.to_dict(),
            "validation": validation
        }
    
    async def refine_preferences(
        self,
        existing_preferences: Dict[str, Any],
        additional_input: str,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Refine existing preferences with new information.
        
        Args:
            existing_preferences: Current preferences as dict
            additional_input: New user input
            request_id: UUID for correlation logging
        
        Returns:
            Dict with updated preferences and validation
        """
        self.logger.info("Refining preferences", extra={
            "request_id": request_id,
            "trip_id": existing_preferences.get("trip_id")
        })
        
        # Convert dict to TripPreferences
        current = TripPreferences.from_dict(existing_preferences)
        
        # Call NLP service for refinement
        updated = await self.nlp_service.refine_preferences(
            existing_preferences=current,
            additional_input=additional_input,
            request_id=request_id
        )
        
        # Validate updated preferences
        validation = updated.validate()
        
        return {
            "preferences": updated.to_dict(),
            "validation": validation
        }
```

---

## Non-Negotiable Rules

### Controller Responsibilities
1. **Orchestrate** service calls, never implement business logic
2. **Validate** inputs before calling services
3. **Format** responses for routes (convert models to dicts)
4. **Log** operations with request_id
5. **Handle** errors and convert to appropriate HTTP responses

### Request ID Propagation
1. **ALWAYS receive** request_id from routes
2. **ALWAYS pass** request_id to services
3. **ALWAYS include** request_id in logs

### Error Handling
1. **Let exceptions propagate** to routes (routes handle HTTP status)
2. **Log errors** at controller level
3. **Add context** to errors (which controller, operation)

### Response Format
1. **Always return** plain dicts (not model instances)
2. **Use consistent structure** (preferences + validation)
3. **Include metadata** when useful (timestamps, versions)

---

## Logging Requirements

### What to Log
- **INFO**: Controller method called, operation completed
- **DEBUG**: Service calls, data transformations
- **WARNING**: Validation warnings, unusual conditions
- **ERROR**: Operation failures (logged before propagating)

### Log Examples
```python
# Method start
logger.info("Extracting preferences", extra={
    "request_id": request_id,
    "controller": "trip",
    "operation": "extract"
})

# Service call
logger.debug("Calling NLP service", extra={
    "request_id": request_id,
    "service": "nlp_extraction",
    "input_length": len(user_input)
})

# Operation complete
logger.info("Preferences extracted", extra={
    "request_id": request_id,
    "valid": validation["valid"],
    "completeness_score": validation["completeness_score"]
})

# Error (before propagating)
logger.error("Preference extraction failed", extra={
    "request_id": request_id,
    "controller": "trip"
}, exc_info=True)
```

---

## Testing Strategy

### Unit Tests Required (Minimum 8)
1. Test extract_preferences (success)
2. Test extract_preferences (validation warning)
3. Test extract_preferences (validation error)
4. Test refine_preferences (add dietary restriction)
5. Test refine_preferences (update budget)
6. Test refine_preferences (preserve existing fields)
7. Test service initialization
8. Test response formatting

### Integration Tests Required (Minimum 3)
1. Test full extract flow (controller → service → client)
2. Test full refine flow
3. Test error propagation

### Test Examples
```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_extract_preferences_success(mock_nlp_service):
    """Test successful preference extraction"""
    controller = TripController()
    controller.nlp_service = mock_nlp_service
    
    # Mock NLP service response
    mock_prefs = TripPreferences(
        start_date="2026-03-15",
        end_date="2026-03-17",
        budget=200.0,
        interests=["history"]
    )
    mock_nlp_service.extract_preferences.return_value = mock_prefs
    
    result = await controller.extract_preferences(
        user_input="Visit Kingston...",
        request_id="req-123"
    )
    
    assert result["preferences"]["start_date"] == "2026-03-15"
    assert result["validation"]["valid"] == False  # Missing required fields
    assert "completeness_score" in result["validation"]

@pytest.mark.asyncio
async def test_refine_preferences_adds_dietary(mock_nlp_service):
    """Test refining with dietary restriction"""
    controller = TripController()
    controller.nlp_service = mock_nlp_service
    
    existing = {
        "start_date": "2026-03-15",
        "end_date": "2026-03-17",
        "budget": 200.0
    }
    
    updated_prefs = TripPreferences(
        start_date="2026-03-15",
        end_date="2026-03-17",
        budget=200.0,
        dietary_restrictions=["vegetarian"]
    )
    mock_nlp_service.refine_preferences.return_value = updated_prefs
    
    result = await controller.refine_preferences(
        existing_preferences=existing,
        additional_input="I'm vegetarian",
        request_id="req-124"
    )
    
    assert "vegetarian" in result["preferences"]["dietary_restrictions"]
```

---

## Error Handling

### Let Errors Propagate
Controllers should **log and re-raise** errors for routes to handle:

```python
try:
    preferences = await self.nlp_service.extract_preferences(...)
except ExternalAPIError as e:
    self.logger.error("NLP service failed", extra={
        "request_id": request_id,
        "service": e.service
    }, exc_info=True)
    raise  # Let routes handle HTTP status
```

### Add Context to Errors
```python
class ControllerError(Exception):
    """Base controller error"""
    def __init__(self, message: str, controller: str, operation: str):
        self.controller = controller
        self.operation = operation
        super().__init__(message)
```

---

## Integration Points

### Used By
- `routes/trip_routes.py` - HTTP request handlers

### Uses
- `services/nlp_extraction_service.py` - Business logic
- `models/trip_preferences.py` - Data structures
- `clients/groq_client.py` - External APIs

---

## Assumptions
1. Routes handle HTTP status codes and error responses
2. Services raise exceptions on failures
3. Models handle their own validation

## Open Questions
1. Should controllers cache service instances or create per-request?
2. Do we need controller-level caching?
3. Should controllers handle rate limiting?

---

**Last Updated**: 2026-02-07  
**Status**: Phase 1 - Documentation Complete, Implementation Pending
