"""
Pydantic models for FastAPI request/response validation.

These are API-boundary schemas only.  Internal business logic continues
to use the existing dataclasses in models/trip_preferences.py and
models/itinerary.py.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ── Request Models ─────────────────────────────────────────────


class ExtractRequest(BaseModel):
    """POST /api/extract — extract trip preferences from natural language."""

    user_input: str = Field(
        ...,
        min_length=1,
        description="Natural language message describing the trip",
        json_schema_extra={"examples": [
            "I want to visit Toronto from March 15-17, 2026. Budget $300. Museums and food."
        ]},
    )


class RefineRequest(BaseModel):
    """POST /api/refine — refine existing preferences with follow-up input."""

    preferences: Dict[str, Any] = Field(
        ...,
        description="Previous preferences dict returned by /api/extract or /api/refine",
    )
    additional_input: str = Field(
        ...,
        min_length=1,
        description="Follow-up user input to refine preferences",
        json_schema_extra={"examples": [
            "I'm vegetarian and want to see the CN Tower"
        ]},
    )


class GenerateItineraryRequest(BaseModel):
    """POST /api/generate-itinerary — generate a full day-by-day itinerary."""

    preferences: Dict[str, Any] = Field(
        ...,
        description=(
            "Complete TripPreferences dict with all 10 required fields: "
            "city, country, location_preference, start_date, end_date, "
            "duration_days, budget, budget_currency, interests, pace"
        ),
    )


# ── Response Models ────────────────────────────────────────────


class ValidationResult(BaseModel):
    """Preference validation output."""

    valid: bool
    issues: List[str] = []
    warnings: List[str] = []
    completeness_score: float = Field(ge=0.0, le=1.0)


class FeasibilityResult(BaseModel):
    """Itinerary feasibility check output."""

    feasible: bool
    issues: List[str] = []
    warnings: List[str] = []


class HealthResponse(BaseModel):
    """GET /api/health response."""

    status: str
    service: str
    primary_llm: str
    model: str
    nlp_service_ready: bool
    error: Optional[str] = None


class ExtractResponse(BaseModel):
    """POST /api/extract response."""

    success: bool
    preferences: Optional[Dict[str, Any]] = None
    validation: Optional[ValidationResult] = None
    bot_message: Optional[str] = None
    saved_to_file: Optional[str] = None
    error: Optional[str] = None


class RefineResponse(BaseModel):
    """POST /api/refine response."""

    success: bool
    preferences: Optional[Dict[str, Any]] = None
    validation: Optional[ValidationResult] = None
    bot_message: Optional[str] = None
    saved_to_file: Optional[str] = None
    error: Optional[str] = None


class GenerateItineraryResponse(BaseModel):
    """POST /api/generate-itinerary response."""

    success: bool
    itinerary: Optional[Dict[str, Any]] = None
    feasibility: Optional[FeasibilityResult] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Generic error envelope returned on failure."""

    success: bool = False
    error: str
