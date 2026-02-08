"""
Tests for ItineraryOrchestrator — preference extraction, enrichment, and fail-soft behavior.

Run:
    pytest test/test_orchestrator.py -v
"""

import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Ensure backend/ is on the import path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend'))

from services.itinerary_orchestrator import ItineraryOrchestrator
from models.trip_preferences import TripPreferences


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_messages(*user_texts: str):
    """Build a minimal conversation history with the given user messages."""
    msgs = [{"role": "system", "content": "system prompt"}]
    for text in user_texts:
        msgs.append({"role": "user", "content": text})
        msgs.append({"role": "assistant", "content": "Ok, got it."})
    return msgs


# ---------------------------------------------------------------------------
# Unit tests — preference extraction
# ---------------------------------------------------------------------------

class TestPreferenceExtraction:
    """Verify regex extraction of dates, budget, interests, pace."""

    def test_single_message_all_fields(self):
        msgs = _make_messages(
            "March 15-17, 2026, budget $300, love museums and food, moderate pace"
        )
        prefs = ItineraryOrchestrator._extract_preferences_from_history(msgs)

        assert prefs.city == "Toronto"
        assert prefs.country == "Canada"
        assert prefs.start_date == "2026-03-15"
        assert prefs.end_date == "2026-03-17"
        assert prefs.duration_days == 3
        assert prefs.budget == 300.0
        assert prefs.pace == "moderate"
        assert "Culture and History" in prefs.interests
        assert "Food and Beverage" in prefs.interests

    def test_multi_turn_extraction(self):
        msgs = _make_messages(
            "March 15-17, 2026",
            "budget is $500",
            "I like nature and parks",
            "packed pace please",
        )
        prefs = ItineraryOrchestrator._extract_preferences_from_history(msgs)

        assert prefs.start_date == "2026-03-15"
        assert prefs.end_date == "2026-03-17"
        assert prefs.budget == 500.0
        assert prefs.pace == "packed"
        assert "Natural Place" in prefs.interests

    def test_iso_date_range(self):
        msgs = _make_messages("I'll be there 2026-06-01 to 2026-06-05, $800 budget, history, relaxed")
        prefs = ItineraryOrchestrator._extract_preferences_from_history(msgs)

        assert prefs.start_date == "2026-06-01"
        assert prefs.end_date == "2026-06-05"
        assert prefs.duration_days == 5

    def test_two_month_date_range(self):
        msgs = _make_messages("June 28 to July 3, 2026. $1000. sports. packed.")
        prefs = ItineraryOrchestrator._extract_preferences_from_history(msgs)

        assert prefs.start_date == "2026-06-28"
        assert prefs.end_date == "2026-07-03"
        assert prefs.budget == 1000.0
        assert prefs.pace == "packed"
        assert "Sport" in prefs.interests

    def test_comma_budget(self):
        msgs = _make_messages("March 1-3, 2026, budget $1,200, food, relaxed")
        prefs = ItineraryOrchestrator._extract_preferences_from_history(msgs)
        assert prefs.budget == 1200.0

    def test_missing_fields_use_defaults(self):
        msgs = _make_messages("just museums please")
        prefs = ItineraryOrchestrator._extract_preferences_from_history(msgs)

        # Should still produce a valid TripPreferences with defaults
        assert prefs.city == "Toronto"
        assert prefs.pace == "moderate"  # default
        assert "Culture and History" in prefs.interests

    def test_booking_type_always_none(self):
        msgs = _make_messages("March 15-17, $300, food, packed")
        prefs = ItineraryOrchestrator._extract_preferences_from_history(msgs)
        assert prefs.booking_type == "none"
        assert prefs.source_location is None


# ---------------------------------------------------------------------------
# Unit tests — enrichment formatting
# ---------------------------------------------------------------------------

class TestEnrichmentFormatting:
    """Verify weather summary, budget summary, and venue extraction."""

    def test_weather_summary_format(self):
        weather_result = {
            "forecasts": [
                {"date": "2026-03-15", "condition": "Partly cloudy", "temp_min_c": -2.0, "temp_max_c": 8.0,
                 "precipitation_mm": 0.0, "precipitation_chance": 10, "wind_speed_kmh": 15.0,
                 "sunrise": "07:23", "sunset": "19:18"},
                {"date": "2026-03-16", "condition": "Rain", "temp_min_c": 1.0, "temp_max_c": 6.0,
                 "precipitation_mm": 5.2, "precipitation_chance": 80, "wind_speed_kmh": 20.0,
                 "sunrise": "07:21", "sunset": "19:19"},
            ]
        }
        summary = ItineraryOrchestrator._format_weather_summary(weather_result)

        assert summary is not None
        assert "2026-03-15" in summary
        assert "Partly cloudy" in summary
        assert "|" in summary  # separator between days

    def test_weather_summary_none_on_error(self):
        assert ItineraryOrchestrator._format_weather_summary(None) is None
        assert ItineraryOrchestrator._format_weather_summary({"forecasts": []}) is None
        assert ItineraryOrchestrator._format_weather_summary({"error": "fail"}) is None

    def test_budget_summary_format(self):
        budget_result = {
            "estimation": {
                "within_budget": True,
                "cheapest_total": {"total": 170.0},
                "average_total": {"total": 240.0},
                "remaining_at_cheapest": 130.0,
                "links": {"airbnb": "https://airbnb.com/test"},
            }
        }
        summary = ItineraryOrchestrator._format_budget_summary(budget_result)

        assert summary is not None
        assert summary["within_budget"] is True
        assert summary["cheapest_total"] == 170.0
        assert summary["remaining_budget"] == 130.0

    def test_budget_summary_none_on_error(self):
        assert ItineraryOrchestrator._format_budget_summary(None) is None
        assert ItineraryOrchestrator._format_budget_summary({"estimation": None}) is None

    def test_extract_venue_names(self):
        text = """Day 1
Morning: Visit the ROM — Royal Ontario Museum (Source: rom, https://www.rom.on.ca)
Afternoon: Lunch at St. Lawrence Market — St. Lawrence Market (Source: st_lawrence_market, https://www.stlawrencemarket.com)
Evening: Walk around — Distillery Historic District (Source: distillery_district, https://www.thedistillerydistrict.com)
"""
        names = ItineraryOrchestrator._extract_venue_names_from_itinerary(text)
        assert names == ["Royal Ontario Museum", "St. Lawrence Market", "Distillery Historic District"]

    def test_extract_venue_names_deduplication(self):
        text = """Day 1
Morning: Visit — CN Tower (Source: cn_tower, https://www.cntower.ca)
Afternoon: Lunch — CN Tower (Source: cn_tower, https://www.cntower.ca)
"""
        names = ItineraryOrchestrator._extract_venue_names_from_itinerary(text)
        assert names == ["CN Tower"]  # deduplicated


# ---------------------------------------------------------------------------
# Unit tests — weather context building
# ---------------------------------------------------------------------------

class TestWeatherContext:
    """Verify weather context is built correctly for LLM prompt."""

    def test_weather_context_with_data(self):
        weather_result = {
            "forecasts": [
                {"date": "2026-03-15", "condition": "Sunny", "temp_min_c": 5.0,
                 "temp_max_c": 15.0, "precipitation_chance": 5},
            ]
        }
        ctx = ItineraryOrchestrator._build_weather_context(weather_result)
        assert "WEATHER FORECAST" in ctx
        assert "2026-03-15" in ctx
        assert "Sunny" in ctx

    def test_weather_context_empty_on_none(self):
        ctx = ItineraryOrchestrator._build_weather_context(None)
        assert "WEATHER FORECAST" not in ctx

    def test_weather_context_empty_on_no_forecasts(self):
        ctx = ItineraryOrchestrator._build_weather_context({"forecasts": []})
        assert "WEATHER FORECAST" not in ctx


# ---------------------------------------------------------------------------
# Integration tests — fail-soft behavior (mocked services)
# ---------------------------------------------------------------------------

class TestFailSoftBehavior:
    """Verify that enrichment failures don't break itinerary generation."""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator with all services mocked."""
        with patch("services.itinerary_orchestrator.WeatherService") as ws, \
             patch("services.itinerary_orchestrator.TripBudgetService") as bs, \
             patch("services.itinerary_orchestrator.GoogleMapsService") as ms, \
             patch("services.itinerary_orchestrator.VenueService") as vs:
            orch = ItineraryOrchestrator()
            return orch

    def test_weather_service_failure_returns_none(self):
        """Weather failure → weather_summary=None, rest works."""
        orch = ItineraryOrchestrator.__new__(ItineraryOrchestrator)
        orch.weather_service = MagicMock()
        orch.weather_service.get_trip_weather.side_effect = Exception("API down")
        orch.budget_service = None
        orch.maps_service = None
        orch.venue_service = None

        prefs = TripPreferences(city="Toronto", country="Canada",
                                start_date="2026-03-15", end_date="2026-03-17",
                                budget=300.0, interests=["Culture and History"], pace="moderate")

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(orch._fetch_weather(loop, prefs))
        loop.close()

        assert result is None  # fail-soft

    def test_budget_service_failure_returns_none(self):
        """Budget failure → budget_summary=None."""
        orch = ItineraryOrchestrator.__new__(ItineraryOrchestrator)
        orch.budget_service = MagicMock()
        orch.budget_service.estimate_trip_budget.side_effect = Exception("Scraping failed")

        prefs = TripPreferences(city="Toronto", country="Canada",
                                start_date="2026-03-15", end_date="2026-03-17",
                                budget=300.0, interests=["Culture and History"], pace="moderate")

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(orch._fetch_budget(loop, prefs))
        loop.close()

        assert result is None

    def test_maps_unavailable_returns_none(self):
        """Maps API not configured → route_data=None."""
        orch = ItineraryOrchestrator.__new__(ItineraryOrchestrator)
        orch.maps_service = MagicMock()
        orch.maps_service.is_available.return_value = False

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(orch._fetch_routes(loop, "some itinerary text"))
        loop.close()

        assert result is None

    def test_venue_fallback_on_db_failure(self):
        """DB unreachable → uses TORONTO_FALLBACK_VENUES."""
        orch = ItineraryOrchestrator.__new__(ItineraryOrchestrator)
        orch.venue_service = MagicMock()
        orch.venue_service.get_toronto_venues.side_effect = Exception("DB down")

        loop = asyncio.new_event_loop()
        venues = loop.run_until_complete(orch._fetch_venues(loop))
        loop.close()

        assert len(venues) == 15  # TORONTO_FALLBACK_VENUES has 15 entries
        assert any(v["place_key"] == "cn_tower" for v in venues)

    def test_venue_fallback_when_no_service(self):
        """No VenueService → falls back to hardcoded venues."""
        orch = ItineraryOrchestrator.__new__(ItineraryOrchestrator)
        orch.venue_service = None

        loop = asyncio.new_event_loop()
        venues = loop.run_until_complete(orch._fetch_venues(loop))
        loop.close()

        assert len(venues) == 15

    def test_venue_ordering_is_deterministic(self):
        """Venues should be sorted by place_key for deterministic prompt."""
        from services.venue_service import TORONTO_FALLBACK_VENUES

        venues = list(TORONTO_FALLBACK_VENUES)
        sorted_venues = sorted(venues, key=lambda v: v.get("place_key", ""))
        keys = [v["place_key"] for v in sorted_venues]

        # Verify sorted order
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Integration test — LLM failure is fatal
# ---------------------------------------------------------------------------

class TestLLMFailureIsFatal:
    """Verify that LLM failure raises an exception (not silent degradation)."""

    def test_llm_failure_raises(self):
        orch = ItineraryOrchestrator.__new__(ItineraryOrchestrator)

        loop = asyncio.new_event_loop()
        with pytest.raises(RuntimeError, match="both Groq and Gemini failed"):
            loop.run_until_complete(
                orch._call_llm(
                    loop,
                    [{"role": "user", "content": "test"}],
                    use_groq=False,
                    use_gemini=False,
                    groq_client=None,
                    gemini_client=None,
                )
            )
        loop.close()
