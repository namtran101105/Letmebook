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


# ── Chat Models (conversational Toronto MVP) ─────────────────


class ChatMessage(BaseModel):
    """Single message in the conversation history."""

    role: str = Field(
        ...,
        description='Message role: "system", "user", or "assistant"',
    )
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    """POST /api/chat — send a conversation turn."""

    messages: List[ChatMessage] = Field(
        default_factory=list,
        description=(
            "Full conversation history. Send an empty list to receive the "
            "greeting message."
        ),
    )
    user_input: Optional[str] = Field(
        None,
        min_length=1,
        description=(
            "The user's latest message. Omit (or null) on the very first "
            "request to trigger the greeting."
        ),
    )


class BudgetSummary(BaseModel):
    """Budget estimation summary returned with itinerary."""

    within_budget: bool = Field(
        description="Whether the estimated costs fit within the user's stated budget.",
    )
    cheapest_total: Optional[float] = Field(
        None, description="Lowest estimated total cost (CAD).",
    )
    average_total: Optional[float] = Field(
        None, description="Average estimated total cost (CAD).",
    )
    remaining_budget: Optional[float] = Field(
        None, description="Budget remaining after cheapest estimate (CAD).",
    )
    links: Optional[Dict[str, Optional[str]]] = Field(
        None,
        description="Booking links (airbnb, skyscanner, etc.).",
    )


class RouteLeg(BaseModel):
    """Single route leg between two venues."""

    leg: int = Field(description="Leg number (1-indexed).")
    origin: str = Field(description="Origin venue/address.")
    destination: str = Field(description="Destination venue/address.")
    duration: Optional[str] = Field(None, description='Travel time, e.g. "18 mins".')
    distance: Optional[str] = Field(None, description='Distance, e.g. "4.2 km".')
    mode: Optional[str] = Field(None, description="Transit mode used.")
    google_maps_link: Optional[str] = Field(None, description="Link to Google Maps directions.")


class ChatResponse(BaseModel):
    """POST /api/chat response."""

    success: bool
    messages: List[ChatMessage] = Field(
        description="Updated conversation history (store client-side).",
    )
    assistant_message: str = Field(
        description="The assistant's reply for this turn.",
    )
    phase: str = Field(
        description=(
            'Current conversation phase: "greeting", "intake", '
            '"confirmed", or "itinerary".'
        ),
    )
    still_need: Optional[List[str]] = Field(
        None,
        description="Fields still missing during intake (null after itinerary).",
    )
    error: Optional[str] = None

    # ── Enrichment fields (populated only in itinerary phase) ──
    weather_summary: Optional[str] = Field(
        None,
        description=(
            "Human-readable weather summary for the trip dates. "
            "Null if weather data unavailable."
        ),
    )
    budget_summary: Optional[BudgetSummary] = Field(
        None,
        description=(
            "Budget estimation with cost breakdown and booking links. "
            "Null if budget estimation unavailable."
        ),
    )
    route_data: Optional[List[RouteLeg]] = Field(
        None,
        description=(
            "Route legs between itinerary venues with travel times and Google Maps links. "
            "Null if route data unavailable."
        ),
    )
