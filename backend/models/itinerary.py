"""
Itinerary data models — structured output of the timetable generator.

Defines Activity, Meal, TravelSegment, ItineraryDay, and Itinerary
dataclasses matching the trip_active_itineraries schema.

Usage:
    itinerary = Itinerary(trip_id="trip_001", ...)
    json_data = itinerary.to_dict()
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class TravelSegment:
    """Transportation between two locations."""

    mode: str = ""                      # car|transit|walking|mixed
    duration_minutes: int = 0
    distance_km: float = 0.0
    from_location: str = ""
    to_location: str = ""
    cost: float = 0.0
    directions: Optional[str] = None    # Google Maps URL or text
    parking_info: Optional[str] = None


@dataclass
class Activity:
    """Single activity in the itinerary."""

    activity_id: str = ""
    venue_name: str = ""
    sequence: int = 0

    # Timing
    planned_start: str = ""             # HH:MM or ISO-8601 datetime
    planned_end: str = ""
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None

    # Details
    category: Optional[str] = None      # maps to user interests
    notes: Optional[str] = None
    duration_reason: Optional[str] = None

    # Status
    status: str = "pending"             # pending|in_progress|completed|skipped|cancelled

    # Cost
    estimated_cost: float = 0.0
    actual_cost: Optional[float] = None

    # Transportation to next activity
    travel_to_next: Optional[TravelSegment] = None

    # Whether this activity came from the Airflow venue database
    from_database: bool = False


@dataclass
class Meal:
    """Meal entry for a day."""

    meal_type: str = ""                 # breakfast|lunch|dinner
    venue_name: str = ""
    planned_time: str = ""              # HH:MM or ISO-8601 datetime
    estimated_cost: float = 0.0
    actual_cost: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class ItineraryDay:
    """Single day in the itinerary."""

    day_number: int = 0
    date: str = ""                      # YYYY-MM-DD

    # Travel from / to starting location
    morning_departure: Optional[TravelSegment] = None
    evening_return: Optional[TravelSegment] = None

    # Content
    activities: List[Activity] = field(default_factory=list)
    meals: List[Meal] = field(default_factory=list)

    # Budget
    daily_budget_allocated: float = 0.0
    daily_budget_spent: float = 0.0

    # Summaries
    total_activities: int = 0
    total_hours: float = 0.0


@dataclass
class Itinerary:
    """Complete trip itinerary."""

    trip_id: str = ""
    itinerary_version: int = 1
    created_at: str = ""
    status: str = "draft"               # draft|active|completed|cancelled

    # Days
    days: List[ItineraryDay] = field(default_factory=list)

    # Summary
    total_budget: float = 0.0
    total_spent: float = 0.0
    total_activities: int = 0
    activities_per_day_avg: float = 0.0
    total_travel_time_hours: float = 0.0

    # Metadata
    pace: Optional[str] = None
    adaptation_count: int = 0
    last_adapted_at: Optional[str] = None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serialisable dictionary."""

        def _segment(seg: Optional[TravelSegment]) -> Optional[Dict[str, Any]]:
            return asdict(seg) if seg else None

        return {
            "trip_id": self.trip_id,
            "itinerary_version": self.itinerary_version,
            "created_at": self.created_at,
            "status": self.status,
            "pace": self.pace,
            "total_budget": self.total_budget,
            "total_spent": self.total_spent,
            "total_activities": self.total_activities,
            "activities_per_day_avg": self.activities_per_day_avg,
            "total_travel_time_hours": self.total_travel_time_hours,
            "adaptation_count": self.adaptation_count,
            "last_adapted_at": self.last_adapted_at,
            "days": [
                {
                    "day_number": day.day_number,
                    "date": day.date,
                    "morning_departure": _segment(day.morning_departure),
                    "activities": [asdict(a) for a in day.activities],
                    "meals": [asdict(m) for m in day.meals],
                    "evening_return": _segment(day.evening_return),
                    "daily_budget_allocated": day.daily_budget_allocated,
                    "daily_budget_spent": day.daily_budget_spent,
                    "total_activities": day.total_activities,
                    "total_hours": day.total_hours,
                }
                for day in self.days
            ],
        }
