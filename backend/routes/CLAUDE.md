# Routes Module - Agent Instructions

**Parent Contexts**:
- `MONVOYAGE/CLAUDE.md` (project-wide architecture, testing conventions)
- `MONVOYAGE/backend/CLAUDE_EMBEDDED.md` (backend-operational rules, MVP requirements)

**Module Purpose**: HTTP route definitions for FastAPI/Flask. Maps URL endpoints to controller functions. Handles request/response formatting, CORS, and middleware.

---

## Module Responsibilities

### Current (Phase 1)
1. **Trip Routes** (`trip_routes.py`) - Endpoints for trip preference extraction and refinement
2. Health check endpoint
3. CORS configuration
4. Request ID middleware

### Planned (Phase 2/3)
5. **Itinerary Routes** (`itinerary_routes.py`) - Endpoints for itinerary generation and management
6. Budget tracking endpoints
7. Venue search endpoints
8. Weather check endpoints
9. Schedule adaptation endpoints

---

## Files in This Module

### `trip_routes.py` (Phase 1 - Current)

**Purpose**: Define HTTP endpoints for trip planning operations.

**Must Include**:
```python
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from backend.controllers.trip_controller import TripController
from backend.controllers.itinerary_controller import ItineraryController
from backend.utils.id_generator import IDGenerator

router = APIRouter(tags=["trips"])
logger = logging.getLogger(__name__)

# Request/Response Models

# --- TripPreferences Schema ---
# REQUIRED fields (10): city, country, start_date, end_date, duration_days,
#   budget, budget_currency, interests, pace, location_preference
# OPTIONAL fields: starting_location (default: from location_preference),
#   hours_per_day (default: 8), transportation_modes (default: ["mixed"]),
#   group_size, group_type, children_ages, dietary_restrictions,
#   accessibility_needs, weather_tolerance, must_see_venues, must_avoid_venues

class ExtractRequest(BaseModel):
    """Request body for /extract endpoint"""
    user_input: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_input": "I want to visit Kingston March 15-17 with $200 budget, interested in history and food, moderate pace"
            }
        }

class RefineRequest(BaseModel):
    """Request body for /refine endpoint"""
    preferences: Dict[str, Any]
    additional_input: str

    class Config:
        json_schema_extra = {
            "example": {
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
                "additional_input": "I'm vegetarian and need wheelchair access"
            }
        }

class GenerateItineraryRequest(BaseModel):
    """Request body for /itinerary/generate endpoint"""
    preferences: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
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
        }

class TripResponse(BaseModel):
    """Standard trip response"""
    success: bool
    preferences: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    itinerary: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

# Health Check
@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Service status and configuration
    """
    return {
        "status": "healthy",
        "service": "MonVoyage Trip Planner",
        "version": "1.0.0",
        "phase": "1",
        "llm": "Gemini (primary) / Groq (fallback)"
    }

# Extract Preferences (Initial)
@router.post("/extract", response_model=TripResponse)
async def extract_preferences(request: Request, body: ExtractRequest):
    """
    Extract trip preferences from natural language.
    
    Args:
        body: Request with user_input field
    
    Returns:
        Extracted preferences and validation results
    
    Raises:
        HTTPException: 400 if validation fails, 500 if processing fails
    """
    request_id = IDGenerator.generate_request_id()
    
    logger.info("Extract preferences request", extra={
        "request_id": request_id,
        "input_length": len(body.user_input)
    })
    
    try:
        controller = TripController()
        result = await controller.extract_preferences(
            user_input=body.user_input,
            request_id=request_id
        )
        
        logger.info("Extract preferences success", extra={
            "request_id": request_id,
            "completeness": result.get("validation", {}).get("completeness_score", 0)
        })
        
        return TripResponse(
            success=True,
            preferences=result["preferences"],
            validation=result["validation"]
        )
        
    except ValidationError as e:
        logger.warning("Validation failed", extra={
            "request_id": request_id,
            "errors": e.issues
        })
        
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Invalid trip preferences",
                "issues": e.issues
            }
        )
        
    except ExternalAPIError as e:
        logger.error("External API failed", extra={
            "request_id": request_id,
            "service": e.service
        }, exc_info=True)
        
        raise HTTPException(
            status_code=503,
            detail={
                "code": "EXTERNAL_API_ERROR",
                "message": f"{e.service} temporarily unavailable",
                "retry_after": 60
            }
        )
        
    except Exception as e:
        logger.error("Unexpected error", extra={
            "request_id": request_id
        }, exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id
            }
        )

# Refine Preferences (Follow-up)
@router.post("/refine", response_model=TripResponse)
async def refine_preferences(request: Request, body: RefineRequest):
    """
    Refine existing preferences with new information.
    
    Args:
        body: Request with preferences and additional_input
    
    Returns:
        Updated preferences and validation results
    """
    request_id = IDGenerator.generate_request_id()
    
    logger.info("Refine preferences request", extra={
        "request_id": request_id,
        "trip_id": body.preferences.get("trip_id")
    })
    
    try:
        controller = TripController()
        result = await controller.refine_preferences(
            existing_preferences=body.preferences,
            additional_input=body.additional_input,
            request_id=request_id
        )
        
        return TripResponse(
            success=True,
            preferences=result["preferences"],
            validation=result["validation"]
        )
        
    except Exception as e:
        logger.error("Refine failed", extra={
            "request_id": request_id
        }, exc_info=True)

        raise HTTPException(status_code=500, detail=str(e))

# Generate Itinerary
@router.post("/itinerary/generate", response_model=TripResponse)
async def generate_itinerary(request: Request, body: GenerateItineraryRequest):
    """
    Generate a trip itinerary from validated preferences.

    Uses Gemini (primary) / Groq (fallback) to generate a feasible
    itinerary based on the 10 required TripPreferences fields:
    city, country, start_date, end_date, duration_days, budget,
    budget_currency, interests, pace, location_preference.

    Args:
        body: Request with validated preferences dict

    Returns:
        Generated itinerary and validation results

    Raises:
        HTTPException: 400 if preferences incomplete, 500 if generation fails
    """
    request_id = IDGenerator.generate_request_id()

    logger.info("Generate itinerary request", extra={
        "request_id": request_id,
        "trip_id": body.preferences.get("trip_id")
    })

    try:
        controller = ItineraryController()
        result = await controller.generate_itinerary(
            preferences=body.preferences,
            request_id=request_id
        )

        return TripResponse(
            success=True,
            preferences=result.get("preferences"),
            itinerary=result.get("itinerary"),
            validation=result.get("validation")
        )

    except Exception as e:
        logger.error("Itinerary generation failed", extra={
            "request_id": request_id
        }, exc_info=True)

        raise HTTPException(status_code=500, detail=str(e))
```

---

## Non-Negotiable Rules

### Request ID Generation
1. **ALWAYS generate request_id** at route level (first thing in handler)
2. **Pass request_id** to all downstream services
3. **Include request_id** in error responses
4. **Log request_id** in all log entries

### Error Handling
1. **Catch specific exceptions first** (ValidationError, ExternalAPIError)
2. **Catch generic Exception last** (fallback)
3. **Return appropriate HTTP status**:
   - 400 for validation errors
   - 401 for authentication errors
   - 403 for authorization errors
   - 404 for not found
   - 429 for rate limiting
   - 500 for internal errors
   - 503 for external service failures
4. **Include error details** in response body

### CORS Configuration
1. **Allow specific origins** (not * in production)
2. **Allow credentials** if needed
3. **Specify allowed methods** (GET, POST, PUT, DELETE)
4. **Specify allowed headers** (Content-Type, Authorization)

### Response Format
1. **Always return JSON**
2. **Use consistent structure**:
   ```json
   {
     "success": true/false,
     "data": {...},
     "error": {...}
   }
   ```
3. **Include metadata** (request_id, timestamp, version)

---

## Logging Requirements

### What to Log
- **INFO**: Request received, request completed, success metrics
- **WARNING**: Validation warnings, slow requests
- **ERROR**: Request failures, API errors
- **CRITICAL**: Service unavailable, critical failures

### Log Examples
```python
# Request start
logger.info("Request received", extra={
    "request_id": request_id,
    "endpoint": "/extract",
    "method": "POST",
    "input_length": len(user_input)
})

# Request success
logger.info("Request completed", extra={
    "request_id": request_id,
    "status_code": 200,
    "response_time_ms": 1250
})

# Request error
logger.error("Request failed", extra={
    "request_id": request_id,
    "status_code": 500,
    "error_type": "ExternalAPIError"
}, exc_info=True)
```

---

## Testing Strategy

### Unit Tests Required (Minimum 8)
1. Test health check endpoint
2. Test extract endpoint (success)
3. Test extract endpoint (validation error)
4. Test extract endpoint (API error)
5. Test refine endpoint (success)
6. Test refine endpoint (error)
7. Test request ID generation
8. Test error response format

### Integration Tests Required (Minimum 3)
1. Test full extract flow (route → controller → service)
2. Test full refine flow
3. Test CORS headers

### Test Examples
```python
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/api/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_extract_success(client: TestClient, mock_controller):
    """Test successful preference extraction"""
    mock_controller.extract_preferences.return_value = {
        "preferences": {...},
        "validation": {"valid": True}
    }
    
    response = client.post("/api/extract", json={
        "user_input": "I want to visit Kingston..."
    })
    
    assert response.status_code == 200
    assert response.json()["success"] == True

def test_extract_validation_error(client: TestClient, mock_controller):
    """Test validation error handling"""
    mock_controller.extract_preferences.side_effect = ValidationError(
        issues=["Budget too low"]
    )
    
    response = client.post("/api/extract", json={
        "user_input": "..."
    })
    
    assert response.status_code == 400
    assert "VALIDATION_ERROR" in response.json()["detail"]["code"]
```

---

## Integration Points

### Calls
- `controllers/trip_controller.py` - Trip preference extraction/refinement handlers
- `controllers/itinerary_controller.py` - Itinerary generation handlers
- `utils/id_generator.py` - Request ID generation

### Called By
- `app.py` - Main application (router registration)
- HTTP clients (frontend, API consumers)

---

## LLM Configuration

- **Primary LLM**: Gemini (configured in `config/settings.py`)
- **Fallback LLM**: Groq (configured in `config/settings.py`)
- All LLM configuration is centralized in `settings.py` (no separate `gemini.py`)
- The NLP extraction and itinerary generation services use Gemini by default, falling back to Groq on failure

---

## TripPreferences Schema Reference

### Required Fields (10)
| Field | Type | Description |
|-------|------|-------------|
| `city` | `str` | Destination city (e.g., "Kingston") |
| `country` | `str` | Destination country (e.g., "Canada") |
| `start_date` | `str` | Trip start date (YYYY-MM-DD) |
| `end_date` | `str` | Trip end date (YYYY-MM-DD) |
| `duration_days` | `int` | Number of trip days |
| `budget` | `float` | Total budget amount |
| `budget_currency` | `str` | Currency code (e.g., "CAD") |
| `interests` | `List[str]` | Activity interests (min 1) |
| `pace` | `str` | "relaxed", "moderate", or "packed" |
| `location_preference` | `str` | Area preference (e.g., "downtown") |

### Optional Fields
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `starting_location` | `str` | from `location_preference` | Specific starting address/hotel |
| `hours_per_day` | `int` | `8` | Available hours per day |
| `transportation_modes` | `List[str]` | `["mixed"]` | Travel modes |
| `group_size` | `int` | - | Number of travelers |
| `group_type` | `str` | - | e.g., "family", "couple", "solo" |
| `children_ages` | `List[int]` | - | Ages of children |
| `dietary_restrictions` | `List[str]` | - | e.g., ["vegetarian"] |
| `accessibility_needs` | `List[str]` | - | e.g., ["wheelchair"] |
| `weather_tolerance` | `str` | - | e.g., "any", "no rain" |
| `must_see_venues` | `List[str]` | - | Required venues |
| `must_avoid_venues` | `List[str]` | - | Venues to avoid |

---

## Assumptions
1. FastAPI handles request parsing and validation
2. Pydantic models validate request bodies
3. CORS middleware is configured at app level
4. Gemini is the primary LLM; Groq is the fallback

## Open Questions
1. Should we rate limit endpoints?
2. Do we need API versioning (/v1/extract)?
3. Should we support batch operations?

---

**Last Updated**: 2026-02-07  
**Status**: Phase 1 - Documentation Complete, Implementation Pending
