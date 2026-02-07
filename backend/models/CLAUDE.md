# Models Module - Agent Instructions

**Parent Contexts**:
- `MONVOYAGE/CLAUDE.md` (project-wide architecture, testing conventions)
- `MONVOYAGE/backend/CLAUDE_EMBEDDED.md` (backend-operational rules, MVP requirements)

**Module Purpose**: Define data structures (dataclasses/Pydantic models) for trip preferences, itineraries, venues, and all domain entities. Enforce validation rules from MVP spec.

---

## Module Responsibilities

### Current (Phase 1)
1. `TripPreferences` - User input data structure for trip planning
2. Validation of required fields (dates, budget, interests, pace, etc.)
3. Budget validation (minimum $50/day from CLAUDE_EMBEDDED.md)
4. Pace validation (relaxed|moderate|packed)
5. JSON serialization/deserialization

### Planned (Phase 2/3)
6. `Itinerary` - Generated trip itinerary with daily schedules
7. `Venue` - Kingston attractions/restaurants
8. `Activity` - Individual itinerary activity with timing
9. `BudgetState` - Real-time budget tracking
10. `WeatherForecast` - Weather data for activity planning
11. MongoDB document serialization

---

## Files in This Module

### `trip_preferences.py`

**Purpose**: Define user trip preferences data model.

**Must Include**:
```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date
from backend.config.settings import settings

@dataclass
class TripPreferences:
    """User trip preferences and constraints"""
    
    # ===== REQUIRED FIELDS (cannot generate itinerary without these) =====
    
    # Location (REQUIRED)
    starting_location: Optional[str] = None  # Hotel/address/area in Kingston
    city: str = "Kingston"
    country: str = "Canada"
    
    # Dates (REQUIRED - both start and end)
    start_date: Optional[str] = None  # YYYY-MM-DD format
    end_date: Optional[str] = None    # YYYY-MM-DD format
    duration_days: Optional[int] = None  # Calculated from dates
    
    # Budget (REQUIRED - minimum $50/day)
    budget: Optional[float] = None  # Total budget
    budget_currency: str = "CAD"
    daily_budget: Optional[float] = None  # Calculated or provided
    
    # Interests (REQUIRED - minimum 1)
    interests: List[str] = field(default_factory=list)
    # Valid: history, food, waterfront, nature, arts, museums, shopping, nightlife
    
    # Time (REQUIRED)
    hours_per_day: Optional[int] = None  # 2-12 hours
    
    # Transportation (REQUIRED - minimum 1 mode)
    transportation_modes: List[str] = field(default_factory=list)
    # Valid: "own car", "rental car", "Kingston Transit", "walking only", "mixed"
    
    # Pace (REQUIRED)
    pace: Optional[str] = None  # "relaxed"|"moderate"|"packed"
    
    # ===== OPTIONAL FIELDS (improve itinerary quality) =====
    
    # Group composition
    group_size: Optional[int] = None
    group_type: Optional[str] = None  # "solo"|"couple"|"family"|"friends"
    children_ages: List[int] = field(default_factory=list)
    
    # Dietary restrictions
    dietary_restrictions: List[str] = field(default_factory=list)
    # e.g., "vegetarian", "vegan", "gluten-free", "nut allergy"
    
    # Accessibility
    accessibility_needs: List[str] = field(default_factory=list)
    # e.g., "wheelchair access", "limited walking", "no stairs"
    
    # Weather
    weather_tolerance: Optional[str] = None
    # "any weather"|"indoor backup"|"indoor only"
    
    # Venue preferences
    must_see_venues: List[str] = field(default_factory=list)
    must_avoid_venues: List[str] = field(default_factory=list)
    
    # Location preference (optional refinement)
    location_preference: Optional[str] = None
    # e.g., "downtown", "waterfront", "near nature"
    
    # Metadata
    trip_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate trip preferences against MVP requirements.
        
        Returns:
            Dict with keys:
            - valid: bool
            - issues: List[str] (blocking errors)
            - warnings: List[str] (non-blocking warnings)
            - completeness_score: float (0.0-1.0)
        """
        issues = []
        warnings = []
        
        # Validate required fields
        if not self.starting_location:
            issues.append("Starting location is required")
        
        if not self.start_date:
            issues.append("Start date is required (YYYY-MM-DD)")
        
        if not self.end_date:
            issues.append("End date is required (YYYY-MM-DD)")
        
        # Validate dates
        if self.start_date and self.end_date:
            try:
                start = date.fromisoformat(self.start_date)
                end = date.fromisoformat(self.end_date)
                
                if end <= start:
                    issues.append("End date must be after start date")
                
                if start < date.today():
                    warnings.append("Start date is in the past")
                
                # Calculate duration
                self.duration_days = (end - start).days + 1
                
            except ValueError as e:
                issues.append(f"Invalid date format: {e}")
        
        # Validate budget (NON-NEGOTIABLE from CLAUDE_EMBEDDED.md)
        if not self.budget and not self.daily_budget:
            issues.append("Budget is required (total or daily)")
        else:
            # Calculate daily budget
            if self.budget and self.duration_days:
                self.daily_budget = self.budget / self.duration_days
            elif self.daily_budget and self.duration_days:
                self.budget = self.daily_budget * self.duration_days
            
            # Enforce minimum daily budget
            if self.daily_budget:
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
        
        # Validate interests
        valid_interests = {
            "history", "food", "waterfront", "nature", 
            "arts", "museums", "shopping", "nightlife"
        }
        
        if not self.interests:
            issues.append("At least one interest category is required")
        else:
            invalid_interests = [i for i in self.interests if i not in valid_interests]
            if invalid_interests:
                warnings.append(
                    f"Unknown interests: {invalid_interests}. "
                    f"Valid: {valid_interests}"
                )
            
            if len(self.interests) > 6:
                warnings.append(
                    f"You selected {len(self.interests)} interests. "
                    "Recommend 2-4 for a focused itinerary."
                )
        
        # Validate hours per day
        if not self.hours_per_day:
            issues.append("Hours per day is required (2-12 hours)")
        elif not 2 <= self.hours_per_day <= 12:
            issues.append("Hours per day must be between 2 and 12")
        
        # Validate transportation
        valid_modes = {"own car", "rental car", "Kingston Transit", "walking only", "mixed"}
        
        if not self.transportation_modes:
            issues.append("At least one transportation mode is required")
        else:
            invalid_modes = [m for m in self.transportation_modes if m not in valid_modes]
            if invalid_modes:
                warnings.append(
                    f"Unknown transportation modes: {invalid_modes}. "
                    f"Valid: {valid_modes}"
                )
            
            # Check location-transportation mismatch
            if "walking only" in self.transportation_modes:
                if self.starting_location and "airport" in self.starting_location.lower():
                    warnings.append(
                        "Walking from airport (~10km to downtown) is impractical. "
                        "Consider transit or car rental."
                    )
        
        # Validate pace (NON-NEGOTIABLE from CLAUDE_EMBEDDED.md)
        if not self.pace:
            issues.append("Pace preference is required (relaxed|moderate|packed)")
        elif self.pace not in ["relaxed", "moderate", "packed"]:
            issues.append(
                f"Invalid pace '{self.pace}'. Must be: relaxed, moderate, or packed"
            )
        
        # Check pace-time mismatches
        if self.pace and self.hours_per_day:
            if self.pace == "packed" and self.hours_per_day < 6:
                warnings.append(
                    f"Packed pace typically needs 8+ hours, but you have {self.hours_per_day}h. "
                    "Consider 'moderate' pace."
                )
            elif self.pace == "relaxed" and self.hours_per_day < 4:
                warnings.append(
                    f"With only {self.hours_per_day}h available, even relaxed pace "
                    "will be limited to 1-2 activities per day."
                )
        
        # Calculate completeness score
        required_fields = [
            self.starting_location,
            self.start_date,
            self.end_date,
            self.budget or self.daily_budget,
            self.interests,
            self.hours_per_day,
            self.transportation_modes,
            self.pace
        ]
        
        optional_fields = [
            self.group_size,
            self.group_type,
            self.dietary_restrictions,
            self.accessibility_needs,
            self.weather_tolerance
        ]
        
        required_count = sum(1 for f in required_fields if f)
        optional_count = sum(1 for f in optional_fields if f)
        
        # Required fields worth 85%, optional 15%
        completeness_score = (
            (required_count / len(required_fields)) * 0.85 +
            (optional_count / len(optional_fields)) * 0.15
        )
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "completeness_score": completeness_score
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "starting_location": self.starting_location,
            "city": self.city,
            "country": self.country,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "duration_days": self.duration_days,
            "budget": self.budget,
            "budget_currency": self.budget_currency,
            "daily_budget": self.daily_budget,
            "interests": self.interests,
            "hours_per_day": self.hours_per_day,
            "transportation_modes": self.transportation_modes,
            "pace": self.pace,
            "group_size": self.group_size,
            "group_type": self.group_type,
            "children_ages": self.children_ages,
            "dietary_restrictions": self.dietary_restrictions,
            "accessibility_needs": self.accessibility_needs,
            "weather_tolerance": self.weather_tolerance,
            "must_see_venues": self.must_see_venues,
            "must_avoid_venues": self.must_avoid_venues,
            "location_preference": self.location_preference,
            "trip_id": self.trip_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TripPreferences":
        """Create instance from dictionary"""
        return cls(**data)
```

---

### `itinerary.py` (Phase 2 - Planned)

**Purpose**: Define generated itinerary data model.

**Must Include**:
```python
@dataclass
class Activity:
    """Single activity in itinerary"""
    activity_id: str
    venue_id: str
    venue_name: str
    sequence: int
    
    # Timing
    planned_start: str  # ISO-8601 datetime
    planned_end: str
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    
    # Status
    status: str = "pending"  # pending|in_progress|completed|skipped|cancelled
    
    # Cost
    estimated_cost: float = 0.0
    actual_cost: Optional[float] = None
    
    # Transportation to next
    travel_to_next: Optional[Dict[str, Any]] = None

@dataclass
class ItineraryDay:
    """Single day in itinerary"""
    day_number: int
    date: str  # YYYY-MM-DD
    activities: List[Activity] = field(default_factory=list)
    meals: List[Dict[str, Any]] = field(default_factory=list)
    daily_budget_allocated: float = 0.0
    daily_budget_spent: float = 0.0

@dataclass
class Itinerary:
    """Complete trip itinerary"""
    trip_id: str
    itinerary_version: int
    created_at: str
    status: str  # draft|active|completed|cancelled
    
    days: List[ItineraryDay] = field(default_factory=list)
    
    total_budget: float = 0.0
    total_spent: float = 0.0
    adaptation_count: int = 0
    last_adapted_at: Optional[str] = None
    
    def validate(self) -> Dict[str, Any]:
        """Validate itinerary feasibility"""
        # Check budget constraints
        # Check time constraints
        # Check transportation feasibility
        # Check venue hours
        pass
```

---

## Non-Negotiable Rules

### Budget Validation
1. **ALWAYS** enforce minimum $50/day (from CLAUDE_EMBEDDED.md)
2. **NEVER** allow budget < $50/day to pass validation
3. **WARN** if budget $50-70/day (tight budget)
4. **CALCULATE** daily budget = total / duration if not provided

### Pace Parameters
Must match CLAUDE_EMBEDDED.md exactly:

**Relaxed**:
- 2-3 activities/day
- 90-120 min/activity
- 20-min buffers
- 90+ min lunch, 120+ min dinner

**Moderate**:
- 4-5 activities/day
- 60-90 min/activity
- 15-min buffers
- 60-90 min meals

**Packed**:
- 6+ activities/day
- 30-60 min/activity
- 5-min buffers
- 45-60 min meals

### Validation Completeness
- **100% score**: All required + all optional fields
- **85-99% score**: All required, some optional missing
- **< 85% score**: Missing required fields (block itinerary generation)

---

## Logging Requirements

### What to Log
- **INFO**: Validation success, completeness score calculated
- **WARNING**: Budget warnings, pace-time mismatches, optional fields missing
- **ERROR**: Validation failures, invalid data types, missing required fields

### Log Examples
```python
logger.info("Trip preferences validated", extra={
    "trip_id": preferences.trip_id,
    "completeness_score": validation["completeness_score"],
    "valid": validation["valid"]
})

logger.warning("Budget is tight", extra={
    "daily_budget": preferences.daily_budget,
    "minimum_required": settings.MIN_DAILY_BUDGET,
    "impact": "Will prioritize affordable options"
})

logger.error("Validation failed", extra={
    "trip_id": preferences.trip_id,
    "issues": validation["issues"]
})
```

---

## Testing Strategy

### Unit Tests Required (Minimum 10)
1. Test TripPreferences creation with all fields
2. Test TripPreferences with only required fields
3. Test budget validation (min $50/day enforcement)
4. Test budget validation with total budget conversion to daily
5. Test date validation (end after start, future dates)
6. Test interests validation (min 1, max 6 warning)
7. Test pace validation (only relaxed|moderate|packed)
8. Test transportation-location mismatch warning
9. Test pace-time mismatch warnings
10. Test completeness score calculation
11. Test JSON serialization (to_dict)
12. Test JSON deserialization (from_dict)

### Negative Tests Required (Minimum 5)
1. Test budget below $50/day (must fail)
2. Test end date before start date (must fail)
3. Test no interests selected (must fail)
4. Test invalid pace value (must fail)
5. Test hours per day outside 2-12 range (must fail)

### Test Examples
```python
def test_minimum_budget_validation():
    """Test that daily budget < $50 is rejected"""
    prefs = TripPreferences(
        starting_location="Downtown Kingston",
        start_date="2026-03-15",
        end_date="2026-03-17",  # 3 days
        budget=100.0,  # $33/day - BELOW minimum
        interests=["history"],
        hours_per_day=8,
        transportation_modes=["walking only"],
        pace="moderate"
    )
    
    validation = prefs.validate()
    
    assert validation["valid"] == False
    assert any("$50" in issue for issue in validation["issues"])
    assert prefs.daily_budget < 50

def test_completeness_score_all_required():
    """Test that all required fields = 85% score"""
    prefs = TripPreferences(
        starting_location="Downtown",
        start_date="2026-03-15",
        end_date="2026-03-17",
        budget=200.0,
        interests=["history", "food"],
        hours_per_day=8,
        transportation_modes=["mixed"],
        pace="moderate"
    )
    
    validation = prefs.validate()
    
    assert validation["completeness_score"] >= 0.85
    assert validation["completeness_score"] < 1.0  # No optional fields

def test_pace_time_mismatch_warning():
    """Test that packed pace + low hours warns user"""
    prefs = TripPreferences(
        starting_location="Downtown",
        start_date="2026-03-15",
        end_date="2026-03-17",
        budget=200.0,
        interests=["history"],
        hours_per_day=4,  # Only 4 hours
        transportation_modes=["mixed"],
        pace="packed"  # Needs 8+ hours
    )
    
    validation = prefs.validate()
    
    assert any("8+ hours" in w for w in validation["warnings"])
```

---

## Error Handling

### Validation Errors
```python
class ValidationError(Exception):
    """Raised when trip preferences fail validation"""
    def __init__(self, issues: List[str], warnings: List[str] = None):
        self.issues = issues
        self.warnings = warnings or []
        super().__init__(f"Validation failed: {issues}")

# Usage
validation = preferences.validate()
if not validation["valid"]:
    raise ValidationError(
        issues=validation["issues"],
        warnings=validation["warnings"]
    )
```

---

## Integration Points

### Used By
- `services/nlp_extraction_service.py` - Creates TripPreferences from NLP
- `services/itinerary_service.py` - Uses validated preferences to generate itinerary
- `controllers/trip_controller.py` - Validates preferences from HTTP requests
- `storage/trip_json_repo.py` - Serializes/deserializes preferences

### Dependencies
- `backend.config.settings` - MIN_DAILY_BUDGET constant
- `datetime` - Date validation
- `typing` - Type hints
- `dataclasses` - Data structure

---

## Assumptions
1. All dates are in YYYY-MM-DD format (ISO-8601)
2. All budgets are in CAD currency
3. Kingston, Ontario is the only supported city
4. Maximum trip duration is 14 days (MVP limit)

## Open Questions
1. Should we support season/month without exact dates in Phase 1?
2. How do we handle timezone conversions for itinerary times?
3. Should validation be automatic on field assignment or manual via validate()?
4. Do we need immutable dataclasses (frozen=True)?

---

**Last Updated**: 2026-02-07  
**Status**: Phase 1 - Documentation Complete, Implementation Pending
