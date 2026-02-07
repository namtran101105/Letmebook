# Backend Embedded Context - MonVoyage Kingston Trip Planner

**Purpose**: This file contains distilled backend-operational rules from the MVP Implementation Guide. All backend modules MUST respect these non-negotiable behaviors.

**Parent Context**: Extends `MONVOYAGE/CLAUDE.md` (project-wide architecture, testing/logging conventions).

---

## Mandatory MVP Features (Non-Negotiable)

All backend modules must support these features:

1. **Natural Language Extraction** - Extract structured trip preferences from user input via Groq/Gemini API
2. **MongoDB Integration** - All persistence via MongoDB collections (no file-based storage in production)
3. **Multi-Modal Transportation** - Support car, Kingston Transit, walking, and mixed modes
4. **Real-Time Weather Tracking** - Weather API integration with outdoor activity warnings
5. **Real-Time Budget Tracking** - Dynamic spending monitor with overspend alerts
6. **Real-Time Schedule Adaptation** - Itinerary re-optimization when users run late/skip activities
7. **Web Scraping with Change Detection** - Apache Airflow pipeline detecting venue content updates

---

## Required Data Fields (TripPreferences Schema)

### Critical Required Inputs (cannot generate itinerary without these):

```python
{
  "starting_location": str,          # REQUIRED - hotel/address/area in Kingston
  "start_date": str,                  # REQUIRED - YYYY-MM-DD format
  "end_date": str,                    # REQUIRED - YYYY-MM-DD format
  "budget": float,                    # REQUIRED - total OR daily (≥ $50/day)
  "interests": List[str],             # REQUIRED - min 1 category
  "hours_per_day": int,               # REQUIRED - 2-12 hours
  "transportation_modes": List[str],  # REQUIRED - min 1 mode
  "pace": str                         # REQUIRED - "relaxed"|"moderate"|"packed"
}
```

### Important Optional Inputs:
- `group_size`: int
- `group_type`: "solo" | "couple" | "family" | "friends"
- `children_ages`: List[int]
- `dietary_restrictions`: List[str]
- `accessibility_needs`: List[str]
- `weather_tolerance`: str
- `must_see_venues`: List[str]
- `must_avoid_venues`: List[str]

---

## Validation Rules (MUST ENFORCE)

### Budget Validation
- **Minimum**: Daily budget MUST BE ≥ $50 (two meals + activities)
- **Reject**: If daily budget < $50
- **Warn**: If daily budget $50-70 ("tight budget")
- **Confirm**: If daily budget ≥ $70 ("good flexibility")

**Calculation**: 
```python
daily_budget = total_budget / num_days
if daily_budget < 50:
    raise ValidationError("Minimum $50/day required for meals and activities")
```

### Date Validation
- **Start date**: Must be today or future
- **End date**: Must be after start_date
- **Duration**: Calculated as `(end_date - start_date).days + 1`

### Interests Validation
- **Minimum**: At least 1 category required
- **Optimal**: 2-4 categories for balanced itinerary
- **Maximum**: 6 categories (warn if exceeded)
- **Valid categories**: history, food, waterfront, nature, arts, museums, shopping, nightlife

### Pace Validation
- **Required**: Must be one of "relaxed", "moderate", or "packed"
- **Pace-Time Mismatch Warnings**:
  - "packed" + hours_per_day < 6 → suggest "moderate"
  - "relaxed" + hours_per_day < 4 → warn limited to 1-2 activities/day

### Transportation-Location Validation
- **Airport + walking**: Warn "Walking from airport (~10km) is impractical"
- **Car modes**: "own car", "rental car"
- **Transit**: "Kingston Transit"
- **Walking**: "walking only"
- **Mixed**: "mixed" (combination)

---

## Pace-Specific Parameters (MUST IMPLEMENT)

### Relaxed Pace
```python
{
  "activities_per_day": (2, 3),
  "minutes_per_activity": (90, 120),
  "buffer_between_activities": 20,  # minutes
  "lunch_duration": 90,              # minutes
  "dinner_duration": 120             # minutes
}
```

### Moderate Pace
```python
{
  "activities_per_day": (4, 5),
  "minutes_per_activity": (60, 90),
  "buffer_between_activities": 15,
  "lunch_duration": 60,
  "dinner_duration": 90
}
```

### Packed Pace
```python
{
  "activities_per_day": (6, 8),
  "minutes_per_activity": (30, 60),
  "buffer_between_activities": 5,
  "lunch_duration": 45,
  "dinner_duration": 60
}
```

---

## MongoDB Collections (Phase 2 - Planned)

### 1. `user_trip_requests`
User constraints and preferences.

**Schema**:
```javascript
{
  _id: ObjectId,
  trip_id: String (UUID),
  user_id: String,
  created_at: ISODate,
  updated_at: ISODate,
  
  // Location
  starting_location: {
    raw_input: String,
    formatted_address: String,
    coordinates: {lat: Number, lng: Number},
    type: String  // "hotel", "address", "area", "airport"
  },
  
  // Dates
  start_date: ISODate,
  end_date: ISODate,
  duration_days: Number,
  
  // Budget
  budget: {
    total: Number,
    daily: Number,
    currency: String (default "CAD")
  },
  
  // Preferences
  interests: [String],
  pace: String,
  hours_per_day: Number,
  transportation_modes: [String],
  
  // Optional
  group: {
    size: Number,
    type: String,
    children_ages: [Number]
  },
  dietary_restrictions: [String],
  accessibility_needs: [String],
  weather_tolerance: String,
  must_see_venues: [String],
  must_avoid_venues: [String]
}
```

### 2. `kingston_venues`
Master database of attractions and restaurants.

**Schema**:
```javascript
{
  _id: ObjectId,
  venue_id: String (UUID),
  name: String,
  type: String,  // "attraction", "restaurant", "activity"
  
  // Location
  address: String,
  coordinates: {lat: Number, lng: Number},
  area: String,  // "downtown", "waterfront", "uptown"
  
  // Categories
  categories: [String],  // maps to interests
  tags: [String],
  
  // Logistics
  typical_duration_minutes: Number,
  price_range: String,  // "$", "$$", "$$$", "$$$$", "free"
  average_cost_per_person: Number,
  
  // Availability
  hours: {
    monday: {open: String, close: String},
    // ... other days
  },
  seasonal_closure: Boolean,
  
  // Accessibility
  wheelchair_accessible: Boolean,
  parking_available: Boolean,
  transit_accessible: Boolean,
  
  // Weather
  outdoor: Boolean,
  weather_dependent: Boolean,
  
  // External
  website: String,
  phone: String,
  
  // Metadata
  last_scraped: ISODate,
  scrape_hash: String,
  change_detected: Boolean,
  popularity_score: Number
}
```

### 3. `trip_active_itineraries`
Generated itineraries with execution tracking.

**Schema**:
```javascript
{
  _id: ObjectId,
  trip_id: String (references user_trip_requests),
  itinerary_version: Number,
  created_at: ISODate,
  status: String,  // "draft", "active", "completed", "cancelled"
  
  // Itinerary days
  days: [
    {
      day_number: Number,
      date: ISODate,
      activities: [
        {
          activity_id: String (UUID),
          venue_id: String (references kingston_venues),
          sequence: Number,
          
          // Timing
          planned_start: ISODate,
          planned_end: ISODate,
          actual_start: ISODate (null if not started),
          actual_end: ISODate (null if not completed),
          
          // Status
          status: String,  // "pending", "in_progress", "completed", "skipped", "cancelled"
          
          // Cost
          estimated_cost: Number,
          actual_cost: Number (null if not completed),
          
          // Transportation to next activity
          travel_to_next: {
            mode: String,
            duration_minutes: Number,
            distance_km: Number,
            directions: String (Google Maps URL or text),
            parking_info: String
          }
        }
      ],
      
      // Meals
      meals: [
        {
          meal_type: String,  // "breakfast", "lunch", "dinner"
          venue_id: String,
          planned_time: ISODate,
          estimated_cost: Number,
          actual_cost: Number
        }
      ],
      
      // Daily summary
      daily_budget_allocated: Number,
      daily_budget_spent: Number
    }
  ],
  
  // Summary
  total_budget: Number,
  total_spent: Number,
  adaptation_count: Number,  // how many times re-optimized
  last_adapted_at: ISODate
}
```

### 4. `trip_budget_state`
Real-time budget tracking.

**Schema**:
```javascript
{
  _id: ObjectId,
  trip_id: String,
  
  // Budget allocation
  total_budget: Number,
  daily_budget: Number,
  
  // Spending by category
  spent: {
    meals: Number,
    activities: Number,
    transportation: Number,
    shopping: Number,
    other: Number,
    total: Number
  },
  
  // Remaining
  remaining: Number,
  remaining_daily: Number,  // for future days
  
  // Alerts
  overspend_risk: Boolean,
  overspend_amount: Number,
  
  // Transactions
  transactions: [
    {
      timestamp: ISODate,
      activity_id: String,
      category: String,
      amount: Number,
      description: String
    }
  ],
  
  last_updated: ISODate
}
```

### 5. `scraped_venue_data`
Raw scraped content and change detection.

**Schema**:
```javascript
{
  _id: ObjectId,
  venue_id: String,
  scrape_timestamp: ISODate,
  
  // Raw content
  raw_html: String,
  content_hash: String (SHA-256),
  
  // Extracted data
  extracted: {
    hours: Object,
    pricing: String,
    description: String,
    special_notices: [String],
    events: [Object]
  },
  
  // Change detection
  previous_hash: String,
  changed: Boolean,
  change_type: [String],  // ["hours", "pricing", "closure"]
  
  // Metadata
  scrape_job_id: String,
  scrape_status: String,  // "success", "failed", "partial"
  error_message: String
}
```

### 6. `venue_change_alerts`
Detected changes from web scraping.

**Schema**:
```javascript
{
  _id: ObjectId,
  venue_id: String,
  detected_at: ISODate,
  
  change_type: String,  // "hours_changed", "pricing_changed", "closed", "reopened"
  severity: String,     // "high", "medium", "low"
  
  // Change details
  old_value: Mixed,
  new_value: Mixed,
  
  // Impact
  affected_trips: [String],  // trip_ids
  notification_sent: Boolean,
  
  // Resolution
  resolved: Boolean,
  resolved_at: ISODate,
  resolution_action: String  // "itinerary_updated", "user_notified", "ignored"
}
```

### 7. `kingston_weather_forecast`
Weather forecasts for planning.

**Schema**:
```javascript
{
  _id: ObjectId,
  forecast_date: ISODate,
  fetched_at: ISODate,
  
  hourly_forecast: [
    {
      hour: Number (0-23),
      temperature_c: Number,
      feels_like_c: Number,
      conditions: String,
      precipitation_chance: Number,
      precipitation_mm: Number,
      wind_speed_kmh: Number,
      
      // Activity suitability
      outdoor_safe: Boolean,
      outdoor_warning: String
    }
  ],
  
  daily_summary: {
    high_c: Number,
    low_c: Number,
    conditions: String,
    precipitation_chance: Number,
    sunrise: String,
    sunset: String
  }
}
```

---

## API Response Standards

### Success Response
```json
{
  "success": true,
  "data": {...},
  "metadata": {
    "request_id": "uuid",
    "timestamp": "ISO-8601",
    "version": "1.0"
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Daily budget must be at least $50",
    "details": {...},
    "request_id": "uuid"
  }
}
```

---

## Logging Requirements (All Modules)

### Log Structure
```python
{
  "timestamp": "ISO-8601",
  "level": "INFO|DEBUG|WARNING|ERROR|CRITICAL",
  "service": "module_name",
  "request_id": "uuid",
  "correlation_id": "uuid",
  "message": "human-readable message",
  "data": {...},
  "user_id": "redacted_if_needed",
  "error_trace": "full_traceback_if_error"
}
```

### What to Log
- **INFO**: Request start/end, major operations, state changes
- **DEBUG**: Detailed processing steps, API calls, data transformations
- **WARNING**: Validation warnings, retry attempts, degraded functionality
- **ERROR**: Operation failures, validation errors, external API failures
- **CRITICAL**: System failures, data corruption, security violations

### Secrets Redaction
ALWAYS redact:
- API keys
- User PII (emails, phone numbers, addresses beyond city)
- Payment information
- Full user messages (log only intent/summary)

### Request Correlation
Every log entry MUST include:
- `request_id`: Unique per HTTP request
- `correlation_id`: Tracks request across services
- `user_id`: If authenticated (redacted appropriately)

---

## Error Handling Standards

### Validation Errors
```python
class ValidationError(Exception):
    """Raised when user input fails validation rules"""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value  # redact if sensitive
```

### External API Errors
```python
class ExternalAPIError(Exception):
    """Raised when external API call fails"""
    def __init__(self, service: str, error: str, retry_count: int = 0):
        self.service = service
        self.error = error
        self.retry_count = retry_count
```

### Business Logic Errors
```python
class ItineraryGenerationError(Exception):
    """Raised when itinerary generation fails feasibility checks"""
    def __init__(self, reason: str, constraints: dict):
        self.reason = reason
        self.constraints = constraints
```

### Error Handling Pattern
```python
try:
    result = process_data(input)
except ValidationError as e:
    logger.warning(f"Validation failed: {e.field} - {e.message}", extra={
        "field": e.field,
        "error_type": "validation"
    })
    return error_response(code="VALIDATION_ERROR", message=e.message)
except ExternalAPIError as e:
    logger.error(f"External API failed: {e.service}", extra={
        "service": e.service,
        "retry_count": e.retry_count
    }, exc_info=True)
    return error_response(code="EXTERNAL_API_ERROR", message="Service temporarily unavailable")
except Exception as e:
    logger.critical("Unexpected error", exc_info=True, extra={
        "error_type": type(e).__name__
    })
    return error_response(code="INTERNAL_ERROR", message="An unexpected error occurred")
```

---

## Testing Requirements (All Modules)

### Test Types Required
1. **Unit Tests**: Test individual functions/classes in isolation
2. **Integration Tests**: Test module interactions (DB, external APIs)
3. **Negative Tests**: Test error handling and validation rejection
4. **Edge Cases**: Test boundary conditions and unusual inputs
5. **Performance Tests**: Test response times and resource usage (when applicable)

### Minimum Test Coverage
- **Critical paths**: 100% coverage
- **Business logic**: 95% coverage
- **Utility functions**: 90% coverage
- **Overall**: 85% coverage

### Test Data
- Use fixtures for common test data
- Never use production API keys in tests
- Mock external API calls
- Use time freezing for date-dependent tests

---

## Assumptions & Open Questions

### Assumptions
1. All dates/times use ISO-8601 format and UTC timezone
2. Currency is CAD unless specified
3. Kingston, Ontario is the only supported city for MVP
4. Groq API is primary NLP provider (Gemini as fallback)
5. Google Maps API is used for geocoding and routing

### Open Questions
1. What is the maximum trip duration supported? (assuming 14 days for MVP)
2. How do we handle multi-city trips? (out of scope for MVP)
3. What is the retry policy for external API failures? (assuming 3 retries with exponential backoff)
4. How do we handle currency conversion? (assuming CAD only for MVP)
5. What is the venue update frequency for web scraping? (assuming daily at 2 AM)

---

**Last Updated**: 2026-02-07  
**Phase**: 1 (NLP Extraction) - Documentation for Current + Planned Features
