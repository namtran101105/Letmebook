# Models Module - Human Documentation

## Overview

The `models/` module defines data structures for all domain entities in the MonVoyage backend. It uses Python dataclasses to represent trip preferences, itineraries, venues, and related entities, with built-in validation logic.

**Current Status**: Phase 1 - Documentation complete, implementation in progress  
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

**Required Fields** (Cannot generate itinerary without these):
- `starting_location` - Where user is staying in Kingston
- `start_date` - Trip start date (YYYY-MM-DD)
- `end_date` - Trip end date (YYYY-MM-DD)
- `budget` - Total budget OR `daily_budget`
- `interests` - List of interest categories (min 1)
- `hours_per_day` - Available hours for activities (2-12)
- `transportation_modes` - How user gets around (min 1)
- `pace` - Trip pace: "relaxed", "moderate", or "packed"

**Optional Fields** (Improve itinerary quality):
- `group_size`, `group_type`, `children_ages`
- `dietary_restrictions`
- `accessibility_needs`
- `weather_tolerance`
- `must_see_venues`, `must_avoid_venues`

**Example Usage**:
```python
from backend.models.trip_preferences import TripPreferences

# Create preferences
prefs = TripPreferences(
    starting_location="Holiday Inn Waterfront",
    start_date="2026-03-15",
    end_date="2026-03-17",
    budget=200.0,
    interests=["history", "food", "waterfront"],
    hours_per_day=8,
    transportation_modes=["own car"],
    pace="moderate",
    group_type="couple",
    dietary_restrictions=["vegetarian"]
)

# Validate
validation = prefs.validate()

if validation["valid"]:
    print(f"✅ Valid! Completeness: {validation['completeness_score']:.0%}")
else:
    print(f"❌ Issues: {validation['issues']}")
    print(f"⚠️  Warnings: {validation['warnings']}")

# Serialize to JSON
json_data = prefs.to_dict()

# Deserialize from JSON
restored = TripPreferences.from_dict(json_data)
```

### `itinerary.py` (Planned - Phase 2)

Generated trip itinerary with daily schedules.

**Key Classes**:
- `Activity` - Single venue visit with timing and cost
- `ItineraryDay` - All activities and meals for one day
- `Itinerary` - Complete multi-day itinerary

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
    ❌ REJECT - "Daily budget must be at least $50"
elif daily_budget < 70:
    ⚠️  WARN - "Budget is tight, prioritizing affordable options"
else:
    ✅ OK - "Good budget flexibility"
```

**Why $50?**
- $15-20 for lunch
- $20-25 for dinner
- $10-15 for activities/entrance fees

### Date Validation

```python
✅ Valid:
- start_date = "2026-03-15", end_date = "2026-03-17"
- start_date is today or future
- end_date is after start_date

❌ Invalid:
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
✅ 1-6 interests allowed
⚠️  Optimal: 2-4 interests
❌ 0 interests: blocked
⚠️  >6 interests: warning (too broad)
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
- "packed" + hours_per_day < 6 → "Consider moderate pace"
- "relaxed" + hours_per_day < 4 → "Limited to 1-2 activities/day"

### Transportation-Location Validation

**Warning Conditions**:
```python
if "walking only" AND "airport" in starting_location:
    ⚠️  "Walking from airport (~10km) is impractical"
    
if "Kingston Transit" AND hours_per_day < 4:
    ⚠️  "Transit may limit flexibility with short timeframe"
```

---

## Completeness Score

Measures how much information the user has provided:

**Calculation**:
```
Score = (required_fields_provided / 8) × 85% 
      + (optional_fields_provided / 5) × 15%
```

**Interpretation**:
- **100%**: All required + all optional fields provided
- **85-99%**: All required, some optional missing → ✅ Can generate itinerary
- **< 85%**: Missing required fields → ❌ Cannot generate itinerary

**Example**:
```python
# All required, no optional = 85% score
prefs = TripPreferences(
    starting_location="Downtown",
    start_date="2026-03-15",
    end_date="2026-03-17",
    budget=200.0,
    interests=["history"],
    hours_per_day=8,
    transportation_modes=["mixed"],
    pace="moderate"
)

validation = prefs.validate()
print(validation["completeness_score"])  # 0.85

# All required + all optional = 100% score
prefs.group_type = "couple"
prefs.dietary_restrictions = ["vegetarian"]
prefs.accessibility_needs = []
prefs.weather_tolerance = "any weather"
prefs.must_see_venues = ["Fort Henry"]

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
    "starting_location": "Downtown Kingston",
    "start_date": "2026-03-15",
    "end_date": "2026-03-17",
    "budget": 200.0,
    "daily_budget": 66.67,
    "interests": ["history", "food"],
    "pace": "moderate",
    ...
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
  "preferences": {...},
  "validation": {
    "valid": false,
    "issues": [
      "Daily budget must be at least $50 (current: $33.33)",
      "At least one interest category is required"
    ],
    "warnings": [
      "Start date is in the past"
    ],
    "completeness_score": 0.62
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

# Run with coverage
pytest backend/tests/models/ --cov=backend/models --cov-report=html
```

### Test Coverage Requirements

- **Overall**: 95% coverage
- **Validation logic**: 100% coverage
- **Edge cases**: All boundary conditions tested

### Key Test Cases

#### Budget Validation
1. ✅ $200 total / 3 days = $66.67/day (valid)
2. ✅ $150 total / 2 days = $75/day (valid, no warnings)
3. ⚠️  $150 total / 3 days = $50/day (valid, but warning)
4. ❌ $100 total / 3 days = $33.33/day (invalid, below minimum)
5. ❌ No budget provided (invalid, required field)

#### Date Validation
6. ✅ start: 2026-03-15, end: 2026-03-17 (valid)
7. ❌ start: 2026-03-17, end: 2026-03-15 (invalid, end before start)
8. ❌ start: 2024-01-01, end: 2024-01-03 (invalid format or past warning)

#### Interests Validation
9. ✅ ["history", "food"] (valid)
10. ❌ [] (invalid, minimum 1 required)
11. ⚠️  ["history", "food", "waterfront", "nature", "arts", "museums", "shopping"] (warning, >6 interests)

#### Pace Validation
12. ✅ "relaxed" (valid)
13. ✅ "moderate" (valid)
14. ✅ "packed" (valid)
15. ❌ "slow" (invalid, not in allowed values)
16. ❌ None (invalid, required field)

#### Pace-Time Mismatch
17. ⚠️  pace="packed", hours_per_day=4 (warning)
18. ⚠️  pace="relaxed", hours_per_day=3 (warning)

#### Completeness Score
19. ✅ All required fields → score ≥ 0.85
20. ✅ All required + all optional → score = 1.0
21. ❌ Missing required fields → score < 0.85

---

## Common Issues

### Issue: "Daily budget must be at least $50"

**Cause**: Total budget is too low for trip duration

**Solution**:
- Increase budget: $50 × number_of_days minimum
- Reduce trip duration
- Example: 3-day trip needs minimum $150

### Issue: "End date must be after start date"

**Cause**: Dates are reversed or same day

**Solution**:
```python
# ❌ Wrong
start_date = "2026-03-17"
end_date = "2026-03-15"

# ✅ Correct
start_date = "2026-03-15"
end_date = "2026-03-17"
```

### Issue: "At least one interest category is required"

**Cause**: Empty interests list

**Solution**:
```python
# ❌ Wrong
interests = []

# ✅ Correct
interests = ["history", "food"]
```

### Issue: Completeness score < 85%

**Cause**: Missing required fields

**Solution**: Check validation response for specific missing fields and provide them.

---

## Future Enhancements (Phase 2/3)

### Phase 2
- [ ] Implement `Itinerary` model
- [ ] Implement `Venue` model
- [ ] Implement `Activity` model
- [ ] Add MongoDB serialization methods
- [ ] Add Pydantic models for FastAPI integration

### Phase 3
- [ ] Implement `BudgetState` model for real-time tracking
- [ ] Implement `WeatherForecast` model
- [ ] Add itinerary feasibility validation
- [ ] Add schedule adaptation logic

---

## API Reference

### `TripPreferences`

#### Constructor
```python
TripPreferences(
    starting_location: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    budget: Optional[float] = None,
    interests: List[str] = [],
    hours_per_day: Optional[int] = None,
    transportation_modes: List[str] = [],
    pace: Optional[str] = None,
    # ... optional fields
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
- Required fields list
- Pace options (relaxed|moderate|packed)
- Pace-specific parameters (activities/day, duration, buffers)

---

**Last Updated**: 2026-02-07  
**Maintained By**: Backend Team  
**Questions**: See `backend/models/CLAUDE.md` for detailed agent instructions
