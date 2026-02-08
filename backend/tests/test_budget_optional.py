"""Test that budget is optional (Bug D fix verification)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


def test_completeness_without_budget():
    """Completeness should reach 1.0 without a budget value."""
    from services.nlp_extraction_service import NLPExtractionService
    from models.trip_preferences import TripPreferences

    service = NLPExtractionService.__new__(NLPExtractionService)
    prefs = TripPreferences(
        city="Toronto",
        country="Canada",
        start_date="2026-03-15",
        end_date="2026-03-17",
        pace="moderate",
        budget=None,  # No budget
    )
    score = service._calculate_completeness(prefs)
    assert score == 1.0, (
        f"Expected completeness 1.0 without budget, got {score}. "
        f"Budget must be removed from required fields."
    )


def test_completeness_without_interests():
    """Completeness should reach 1.0 without interests (interests are optional)."""
    from services.nlp_extraction_service import NLPExtractionService
    from models.trip_preferences import TripPreferences

    service = NLPExtractionService.__new__(NLPExtractionService)
    prefs = TripPreferences(
        city="Toronto",
        country="Canada",
        start_date="2026-03-15",
        end_date="2026-03-17",
        pace="moderate",
        interests=[],  # No interests
    )
    score = service._calculate_completeness(prefs)
    assert score == 1.0, (
        f"Expected completeness 1.0 without interests, got {score}."
    )


def test_completeness_missing_required_fields():
    """Completeness < 1.0 when actual required fields are missing."""
    from services.nlp_extraction_service import NLPExtractionService
    from models.trip_preferences import TripPreferences

    service = NLPExtractionService.__new__(NLPExtractionService)
    prefs = TripPreferences(
        city="Toronto",
        country=None,   # Missing
        start_date=None,  # Missing
        end_date=None,    # Missing
        pace="moderate",
    )
    score = service._calculate_completeness(prefs)
    assert score < 1.0, "Completeness should be < 1.0 when required fields missing"


def test_itinerary_service_accepts_no_budget():
    """ItineraryService._validate_preferences must not reject missing budget."""
    from services.itinerary_service import ItineraryService

    svc = ItineraryService.__new__(ItineraryService)
    svc.logger = __import__("logging").getLogger(__name__)

    prefs = {
        "city": "Toronto",
        "country": "Canada",
        "start_date": "2026-03-15",
        "end_date": "2026-03-17",
        "duration_days": 3,
        "pace": "moderate",
        "interests": [],
        "location_preference": "downtown",
        "budget": None,  # Optional
    }
    # Should not raise
    validated = svc._validate_preferences(prefs, "test-budget-optional")
    assert validated["city"] == "Toronto"
