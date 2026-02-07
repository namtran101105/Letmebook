# Models Module - Human Documentation

## Overview

The `models/` module defines data structures for all domain entities in the MonVoyage backend. It uses Python dataclasses to represent trip preferences, itineraries, venues, and related entities, with built-in validation logic.

**Current Status**: Phase 1 - TripPreferences (10 required fields) and Itinerary models implemented
**Dependencies**: `dataclasses`, `typing`, `datetime`, `backend.config.settings`

---

## Purpose

- Define structured data models for trip planning
- Validate user inputs against MVP requirements
- Enforce business rules (minimum budget, required fields)
- Provide JSON serialization for API responses
- Ensure type safety across the application

---

## Files

### `trip_preferences.py`

User trip preferences and constraints.

**Key Class**: `TripPreferences`

**Required Fields (10)** -- Cannot generate itinerary without these:
- `city` - City name (default: "Kingston")
- `country` - Country name (default: "Canada")
- `location_preference` - Area preference (e.g., "downtown", "waterfront", "near nature")
- `start_date` - Trip start date (YYYY-MM-DD)
- `end_date` - Trip end date (YYYY-MM-DD)
- `duration_days` - Number of days (calculated from dates)
- `budget` - Total budget OR `daily_budget`
- `budget_currency` - Currency code (default: "CAD")
- `interests` - List of interest categories (min 1)
- `pace` - Trip pace: "relaxed", "moderate", or "packed"

**Optional Fields (with defaults)**:
- `starting_location` - Hotel/address (default: derived from `location_preference`)
- `hours_per_day` - Available hours for activities (default: 8)
- `transportation_modes` - How user gets around (default: `["mixed"]`)
- `group_size`, `group_type`, `children_ages`
- `dietary_restrictions`
- `accessibility_needs`
- `weather_tolerance`
- `must_see_venues`, `must_avoid_venues`

**Example Usage**:
```python
from models.trip_preferences import TripPreferences

# Create preferences with required fields
prefs = TripPreferences(
    city="Kingston",
    country="Canada",
    location_preference="downtown",
    start_date="2026-03-15",
    end_date="2026-03-17",
    budget=200.0,
    interests=["history", "food", "waterfront"],
    pace="moderate",
    # Optional fields
    starting_location="Holiday Inn Waterfront",
    group_type="couple",
    dietary_restrictions=["vegetarian"]
)

# Validate
validation = prefs.validate()

if validation["valid"]:
    print(f"Valid! Completeness: {validation['completeness_score']:.0%}")
else:
    print(f"Issues: {validation['issues']}")
    print(f"Warnings: {validation['warnings']}")

# Serialize to JSON
json_data = prefs.to_dict()

# Deserialize from JSON
restored = TripPreferences.from_dict(json_data)
```

### `itinerary.py` (Implemented)

Generated trip itinerary with daily schedules.

**Key Classes**:
- `Activity` - Single venue visit with timing, cost, and status
- `Meal` - Meal slot with venue, timing, cost, and dietary notes
- `TravelSegment` - Travel between two points with mode, duration, and distance
- `ItineraryDay` - All activities, meals, and travel for one day
- `Itinerary` - Complete multi-day itinerary with budget tracking

**Example Usage**:
```python
from models.itinerary import Itinerary, ItineraryDay, Activity, Meal, TravelSegment

# Create an activity
activity = Activity(
    activity_id="a1",
    venue_id="v-fort-henry",
    venue_name="Fort Henry",
    sequence=1,
    planned_start="2026-03-15T09:00:00",
    planned_end="2026-03-15T11:00:00",
    estimated_cost=25.0
)

# Create a meal
lunch = Meal(
    meal_type="lunch",
    venue_name="Chez Piggy",
    planned_start="2026-03-15T12:00:00",
    planned_end="2026-03-15T13:15:00",
    estimated_cost=30.0,
    dietary_notes=["vegetarian options available"]
)

# Create travel segment
travel = TravelSegment(
    from_venue="Fort Henry",
    to_venue="Chez Piggy",
    mode="car",
    estimated_duration_minutes=15,
    estimated_distance_km=8.5
)

# Create a day
day1 = ItineraryDay(
    day_number=1,
    date="2026-03-15",
    activities=[activity],
    meals=[lunch],
    travel_segments=[travel],
    daily_budget_allocated=80.0
)

# Create full itinerary
itinerary = Itinerary(
    trip_id="trip-abc123",
    itinerary_version=1,
    created_at="2026-03-15T00:00:00Z",
    status="draft",
    days=[day1],
    total_budget=200.0
)

# Validate
validation = itinerary.validate()
```

---

## Validation Rules

### Budget Validation (Non-Negotiable)

**Minimum Daily Budget**: $50 CAD

This is a **hard requirement** from the MVP spec. Users cannot proceed with less than $50/day.

**Validation Logic**:
```python
# Calculate daily budget
if budget and duration_days:
    daily_budget = budget / duration_days

# Enforce minimum
if daily_budget < 50:
    REJECT - "Daily budget must be at least $50"
elif daily_budget < 70:
    WARN - "Budget is tight, prioritizing affordable options"
else:
    OK - "Good budget flexibility"
```

**Why $50?**
- $15-20 for lunch
- $20-25 for dinner
- $10-15 for activities/entrance fees

### Required Fields Validation

All 10 required fields must be present:
```python
Required (must be provided or have valid default):
1. city = "Kingston" (default)
2. country = "Canada" (default)
3. location_preference (user must provide)
4. start_date (user must provide, YYYY-MM-DD)
5. end_date (user must provide, YYYY-MM-DD)
6. duration_days (calculated from dates)
7. budget (user must provide, total or daily)
8. budget_currency = "CAD" (default)
9. interests (user must provide, min 1)
10. pace (user must provide: relaxed|moderate|packed)
```

### Date Validation

```python
Valid:
- start_date = "2026-03-15", end_date = "2026-03-17"
- start_date is today or future
- end_date is after start_date

Invalid:
- end_date before or same as start_date
- start_date in the past (warns, doesn't block)
- Invalid format (not YYYY-MM-DD)
```

### Interests Validation

```python
Valid Categories:
- history, food, waterfront, nature
- arts, museums, shopping, nightlife

Rules:
1-6 interests allowed
Optimal: 2-4 interests
0 interests: blocked
>6 interests: warning (too broad)
```

### Pace Validation (Non-Negotiable)

**Must be exactly one of**: `"relaxed"`, `"moderate"`, or `"packed"`

**Pace Impact** (from MVP spec):

| Pace | Activities/Day | Minutes/Activity | Buffer | Meals |
|------|----------------|------------------|--------|-------|
| **Relaxed** | 2-3 | 90-120 min | 20 min | 90/120 min |
| **Moderate** | 4-5 | 60-90 min | 15 min | 60/90 min |
| **Packed** | 6+ | 30-60 min | 5 min | 45/60 min |

**Pace-Time Mismatch Warnings**:
- "packed" + hours_per_day < 6 -> "Consider moderate pace"
- "relaxed" + hours_per_day < 4 -> "Limited to 1-2 activities/day"

### Transportation-Location Validation

**Warning Conditions**:
```python
if "walking only" AND "airport" in starting_location:
    WARN "Walking from airport (~10km) is impractical"

if "Kingston Transit" AND hours_per_day < 4:
    WARN "Transit may limit flexibility with short timeframe"
```

---

## Completeness Score

Measures how much information the user has provided:

**Calculation**:
```
Score = (required_fields_provided / 10) x 85%
      + (optional_fields_provided / 6) x 15%
```

**Interpretation**:
- **100%**: All 10 required + all optional fields provided
- **85-99%**: All required, some optional missing -> Can generate itinerary
- **< 85%**: Missing required fields -> Cannot generate itinerary

**Example**:
```python
# All required, no optional = 85% score
prefs = TripPreferences(
    city="Kingston",
    country="Canada",
    location_preference="downtown",
    start_date="2026-03-15",
    end_date="2026-03-17",
    budget=200.0,
    interests=["history"],
    pace="moderate"
)

validation = prefs.validate()
print(validation["completeness_score"])  # 0.85

# All required + all optional = 100% score
prefs.starting_location = "Holiday Inn"
prefs.group_type = "couple"
prefs.group_size = 2
prefs.dietary_restrictions = ["vegetarian"]
prefs.accessibility_needs = ["wheelchair access"]
prefs.weather_tolerance = "any weather"

validation = prefs.validate()
print(validation["completeness_score"])  # 1.0
```

---

## API Integration

### Validation Response Format

```python
{
    "valid": bool,
    "issues": [str],      # Blocking errors
    "warnings": [str],    # Non-blocking warnings
    "completeness_score": float  # 0.0 to 1.0
}
```

### HTTP Response Example

**Valid Preferences**:
```json
{
  "success": true,
  "preferences": {
    "city": "Kingston",
    "country": "Canada",
    "location_preference": "downtown",
    "starting_location": "Downtown Kingston",
    "start_date": "2026-03-15",
    "end_date": "2026-03-17",
    "budget": 200.0,
    "daily_budget": 66.67,
    "interests": ["history", "food"],
    "pace": "moderate",
    "hours_per_day": 8,
    "transportation_modes": ["mixed"]
  },
  "validation": {
    "valid": true,
    "issues": [],
    "warnings": [],
    "completeness_score": 0.95
  }
}
```

**Invalid Preferences**:
```json
{
  "success": false,
  "preferences": {},
  "validation": {
    "valid": false,
    "issues": [
      "Daily budget must be at least $50 (current: $33.33)",
      "At least one interest category is required",
      "Location preference is required"
    ],
    "warnings": [
      "Start date is in the past"
    ],
    "completeness_score": 0.51
  }
}
```

---

## Testing

### Running Tests

```bash
# Run all model tests
pytest backend/tests/models/test_trip_preferences.py -v

# Run specific test
pytest backend/tests/models/test_trip_preferences.py::test_minimum_budget_validation -v

# Run itinerary model tests
pytest backend/tests/models/test_itinerary.py -v

# Run with coverage
pytest backend/tests/models/ --cov=backend/models --cov-report=html
```

### Test Coverage Requirements

- **Overall**: 95% coverage
- **Validation logic**: 100% coverage
- **Edge cases**: All boundary conditions tested

### Key Test Cases

#### Budget Validation
1. $200 total / 3 days = $66.67/day (valid)
2. $150 total / 2 days = $75/day (valid, no warnings)
3. $150 total / 3 days = $50/day (valid, but warning)
4. $100 total / 3 days = $33.33/day (invalid, below minimum)
5. No budget provided (invalid, required field)

#### Date Validation
6. start: 2026-03-15, end: 2026-03-17 (valid)
7. start: 2026-03-17, end: 2026-03-15 (invalid, end before start)
8. start: 2024-01-01, end: 2024-01-03 (past date warning)

#### Required Fields Validation
9. All 10 required fields present (valid, score >= 0.85)
10. Missing location_preference (invalid)
11. Missing city (invalid)
12. Missing pace (invalid)

#### Interests Validation
13. ["history", "food"] (valid)
14. [] (invalid, minimum 1 required)
15. 7+ interests (warning, >6 interests)

#### Pace Validation
16. "relaxed" (valid)
17. "moderate" (valid)
18. "packed" (valid)
19. "slow" (invalid, not in allowed values)
20. None (invalid, required field)

#### Pace-Time Mismatch
21. pace="packed", hours_per_day=4 (warning)
22. pace="relaxed", hours_per_day=3 (warning)

#### Default Values
23. hours_per_day defaults to 8
24. transportation_modes defaults to ["mixed"]

#### Completeness Score
25. All required fields -> score >= 0.85
26. All required + all optional -> score = 1.0
27. Missing required fields -> score < 0.85

#### Itinerary Model
28. Itinerary with budget within limits (valid)
29. Itinerary with costs exceeding budget (invalid)
30. Activity, Meal, TravelSegment creation

---

## Common Issues

### Issue: "Daily budget must be at least $50"

**Cause**: Total budget is too low for trip duration

**Solution**:
- Increase budget: $50 x number_of_days minimum
- Reduce trip duration
- Example: 3-day trip needs minimum $150

### Issue: "Location preference is required"

**Cause**: User did not specify a preferred area in Kingston

**Solution**:
```python
# Provide a location preference
location_preference = "downtown"  # or "waterfront", "near nature"
```

### Issue: "End date must be after start date"

**Cause**: Dates are reversed or same day

**Solution**:
```python
# Wrong
start_date = "2026-03-17"
end_date = "2026-03-15"

# Correct
start_date = "2026-03-15"
end_date = "2026-03-17"
```

### Issue: "At least one interest category is required"

**Cause**: Empty interests list

**Solution**:
```python
# Wrong
interests = []

# Correct
interests = ["history", "food"]
```

### Issue: Completeness score < 85%

**Cause**: Missing required fields

**Solution**: Check validation response for specific missing fields and provide them.

---

## Future Enhancements (Phase 2/3)

### Phase 2
- [ ] Implement `Venue` model
- [ ] Add MongoDB serialization methods
- [ ] Add Pydantic models for FastAPI integration

### Phase 3
- [ ] Implement `BudgetState` model for real-time tracking
- [ ] Implement `WeatherForecast` model
- [ ] Add schedule adaptation logic

---

## API Reference

### `TripPreferences`

#### Constructor
```python
TripPreferences(
    city: str = "Kingston",
    country: str = "Canada",
    location_preference: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    budget: Optional[float] = None,
    interests: List[str] = [],
    pace: Optional[str] = None,
    # Optional with defaults
    starting_location: Optional[str] = None,
    hours_per_day: int = 8,
    transportation_modes: List[str] = ["mixed"],
    # ... other optional fields
)
```

#### Methods

**`validate() -> Dict[str, Any]`**

Validates preferences against MVP requirements.

Returns:
```python
{
    "valid": bool,              # Can generate itinerary?
    "issues": List[str],        # Blocking errors
    "warnings": List[str],      # Non-blocking warnings
    "completeness_score": float # 0.0 to 1.0
}
```

**`to_dict() -> Dict[str, Any]`**

Converts to dictionary for JSON serialization.

**`from_dict(data: Dict[str, Any]) -> TripPreferences`**

Creates instance from dictionary.

### `Itinerary`

#### Constructor
```python
Itinerary(
    trip_id: str,
    itinerary_version: int,
    created_at: str,
    status: str,  # draft|active|completed|cancelled
    days: List[ItineraryDay] = [],
    total_budget: float = 0.0,
    total_spent: float = 0.0
)
```

#### Methods

**`validate() -> Dict[str, Any]`**

Validates itinerary feasibility (budget, time, transportation).

---

## Contributing

When modifying validation rules:

1. **Check CLAUDE_EMBEDDED.md** for non-negotiable requirements
2. **Update validation logic** in `validate()` method
3. **Add tests** for new validation rules
4. **Update this README** with examples
5. **Update CLAUDE.md** with agent instructions

**Never change** without consulting MVP spec:
- Minimum daily budget ($50)
- Required fields list (10 required)
- Pace options (relaxed|moderate|packed)
- Pace-specific parameters (activities/day, duration, buffers)

---

**Last Updated**: 2026-02-07
**Maintained By**: Backend Team
**Questions**: See `backend/models/CLAUDE.md` for detailed agent instructions
