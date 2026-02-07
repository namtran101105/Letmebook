"""
TripPreferences data model — user trip preferences and constraints.

Defines the canonical schema with 10 required fields and optional fields.
Includes validation logic enforcing MVP rules (budget, pace, dates, interests).

Usage:
    prefs = TripPreferences.from_dict(json_data)
    result = prefs.validate()
    if not result["valid"]:
        raise ValidationError(result["issues"])
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date


@dataclass
class TripPreferences:
    """User trip preferences and constraints."""

    # ===== REQUIRED FIELDS (10) — cannot generate itinerary without these =====

    # Location
    city: Optional[str] = None                       # e.g., "Kingston"
    country: Optional[str] = None                    # e.g., "Canada"
    location_preference: Optional[str] = None        # e.g., "City center near public transportation"

    # Dates
    start_date: Optional[str] = None                 # YYYY-MM-DD
    end_date: Optional[str] = None                   # YYYY-MM-DD
    duration_days: Optional[int] = None              # Must match date range

    # Budget
    budget: Optional[float] = None                   # Total trip budget
    budget_currency: Optional[str] = None            # e.g., "CAD"

    # Preferences
    interests: List[str] = field(default_factory=list)   # Min 1, max 6
    pace: Optional[str] = None                            # relaxed|moderate|packed

    # ===== OPTIONAL FIELDS — improve itinerary quality =====

    # Derived / defaulted
    starting_location: Optional[str] = None          # Default: from location_preference
    daily_budget: Optional[float] = None             # Calculated: budget / duration_days
    hours_per_day: Optional[int] = None              # Default: 8
    transportation_modes: List[str] = field(default_factory=list)  # Default: ["mixed"]

    # Group composition
    group_size: Optional[int] = None
    group_type: Optional[str] = None                 # solo|couple|family|friends
    children_ages: List[int] = field(default_factory=list)

    # Dietary / accessibility
    dietary_restrictions: List[str] = field(default_factory=list)
    accessibility_needs: List[str] = field(default_factory=list)

    # Weather
    weather_tolerance: Optional[str] = None          # any weather|indoor backup|indoor only

    # Venue preferences
    must_see_venues: List[str] = field(default_factory=list)
    must_avoid_venues: List[str] = field(default_factory=list)

    # Metadata
    trip_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def validate(self) -> Dict[str, Any]:
        """
        Validate trip preferences against MVP requirements.

        Returns:
            Dict with keys: valid (bool), issues (List[str]),
            warnings (List[str]), completeness_score (float 0.0-1.0).
        """
        from backend.config.settings import settings

        issues: List[str] = []
        warnings: List[str] = []

        # --- Required field checks ---
        if not self.city:
            issues.append("City is required")
        if not self.country:
            issues.append("Country is required")
        if not self.location_preference:
            issues.append("Location preference is required")
        if not self.start_date:
            issues.append("Start date is required (YYYY-MM-DD)")
        if not self.end_date:
            issues.append("End date is required (YYYY-MM-DD)")
        if self.budget is None:
            issues.append("Budget is required")
        if not self.budget_currency:
            issues.append("Budget currency is required")
        if not self.interests:
            issues.append("At least one interest category is required")
        if not self.pace:
            issues.append("Pace preference is required (relaxed|moderate|packed)")

        # --- Date validation ---
        if self.start_date and self.end_date:
            try:
                start = date.fromisoformat(self.start_date)
                end = date.fromisoformat(self.end_date)
                if end <= start:
                    issues.append("End date must be after start date")
                if start < date.today():
                    warnings.append("Start date is in the past")
                calculated_duration = (end - start).days + 1
                if self.duration_days is None:
                    self.duration_days = calculated_duration
                elif self.duration_days != calculated_duration:
                    warnings.append(
                        f"duration_days ({self.duration_days}) does not match "
                        f"date range ({calculated_duration}). Using date range."
                    )
                    self.duration_days = calculated_duration
            except ValueError as exc:
                issues.append(f"Invalid date format: {exc}")

        # duration_days required
        if self.duration_days is None:
            issues.append("duration_days is required")

        # --- Budget validation (NON-NEGOTIABLE) ---
        if self.budget is not None and self.duration_days:
            self.daily_budget = self.budget / self.duration_days
            if self.daily_budget < settings.MIN_DAILY_BUDGET:
                issues.append(
                    f"Daily budget must be at least ${settings.MIN_DAILY_BUDGET} "
                    f"for meals and activities (current: ${self.daily_budget:.2f})"
                )
            elif self.daily_budget < 70:
                warnings.append(
                    f"Budget is tight (${self.daily_budget:.2f}/day). "
                    "We'll prioritize affordable dining and free attractions."
                )

        # --- Interest validation ---
        if self.interests and len(self.interests) > 6:
            warnings.append(
                f"You selected {len(self.interests)} interests. "
                "Recommend 2-4 for a focused itinerary."
            )

        # --- Pace validation ---
        if self.pace and self.pace not in settings.VALID_PACES:
            issues.append(
                f"Invalid pace '{self.pace}'. Must be: relaxed, moderate, or packed"
            )

        # --- Apply defaults for optional fields ---
        if not self.starting_location:
            self.starting_location = self.location_preference or "Downtown Kingston"
        if not self.hours_per_day:
            self.hours_per_day = 8
        if not self.transportation_modes:
            self.transportation_modes = ["mixed"]

        # --- Completeness score ---
        required_fields = [
            self.city, self.country, self.location_preference,
            self.start_date, self.end_date, self.duration_days,
            self.budget, self.budget_currency, self.interests, self.pace,
        ]
        optional_fields = [
            self.group_size, self.group_type, self.dietary_restrictions,
            self.accessibility_needs, self.weather_tolerance,
        ]
        required_count = sum(1 for f in required_fields if f)
        optional_count = sum(1 for f in optional_fields if f)
        completeness_score = (
            (required_count / len(required_fields)) * 0.85
            + (optional_count / len(optional_fields)) * 0.15
        )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "completeness_score": round(completeness_score, 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "city": self.city,
            "country": self.country,
            "location_preference": self.location_preference,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "duration_days": self.duration_days,
            "budget": self.budget,
            "budget_currency": self.budget_currency,
            "daily_budget": self.daily_budget,
            "interests": self.interests,
            "pace": self.pace,
            "starting_location": self.starting_location,
            "hours_per_day": self.hours_per_day,
            "transportation_modes": self.transportation_modes,
            "group_size": self.group_size,
            "group_type": self.group_type,
            "children_ages": self.children_ages,
            "dietary_restrictions": self.dietary_restrictions,
            "accessibility_needs": self.accessibility_needs,
            "weather_tolerance": self.weather_tolerance,
            "must_see_venues": self.must_see_venues,
            "must_avoid_venues": self.must_avoid_venues,
            "trip_id": self.trip_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TripPreferences":
        """Create instance from dictionary, ignoring unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)
