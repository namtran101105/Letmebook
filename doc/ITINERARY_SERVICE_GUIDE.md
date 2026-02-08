# Itinerary Service - Complete Technical Guide

**File**: `backend/services/itinerary_service.py` (721 lines)  
**Purpose**: Generate complete day-by-day itineraries with schedules, activities, meals, and costs  
**Status**: ✅ Implemented, ⚠️ Has import bugs (blocking)  
**Language**: Python 3.11.5

---

## 📋 Quick Overview

The `ItineraryService` is responsible for:
- ✅ Taking validated trip preferences as input
- ✅ Building a detailed prompt for Gemini 2.5-Flash
- ✅ Calling Gemini API to generate a day-by-day schedule
- ✅ Parsing the JSON response into structured data
- ✅ Validating the itinerary for feasibility
- ✅ Returning a complete itinerary object

**Time**: Generates itinerary in 30-60 seconds per request  
**Cost**: Uses Gemini 2.5-Flash API (~$0.10 per request)

---

## 🔄 How It Works: Step-by-Step

### Step 1: Input - Trip Preferences

**Source**: Comes from user's validated preferences (NLP extraction)

**Format** (Python dict):
```python
{
    # Required: Location
    "city": "Kingston",
    "country": "Canada",
    "location_preference": "downtown",
    
    # Required: Dates
    "start_date": "2026-05-10",
    "end_date": "2026-05-12",
    "duration_days": 3,
    
    # Required: Budget
    "budget": 900.0,
    "budget_currency": "CAD",
    
    # Required: Preferences
    "interests": ["museums", "food", "waterfront"],
    "pace": "moderate",
    
    # Optional: Already set by Gemini
    "starting_location": "Downtown Kingston",
    "hours_per_day": 8,
    "transportation_modes": ["mixed"],
    "group_size": None,
    "dietary_restrictions": [],
    "accessibility_needs": [],
}
```

### Step 2: Validation - Check all fields

**Code Location**: Lines 305-359  
**Method**: `_validate_preferences(prefs, request_id)`

**Checks**:
```python
✅ All 10 required fields present
✅ Dates are valid and in correct order
✅ End date > start_date
✅ Duration days matches date range
✅ Daily budget >= $50 (MVP requirement)
✅ Pace is one of: relaxed, moderate, packed
✅ At least 1 interest selected
```

**Example validation**:
```python
# Input
budget = 900
duration_days = 3
daily_budget = 900 / 3 = 300

# Check
300 >= 50? ✅ YES → PASS
```

**Output**: Validated preferences dict with defaults filled in

---

### Step 3: Prompt Building - Tell Gemini what to do

**Code Location**: Lines 361-403  
**Method**: `_build_generation_prompt(prefs)`

**Creates**: A detailed prompt that tells Gemini:
- Where the trip is (Kingston, Canada)
- When (May 10-12)
- How much budget per day ($300/day)
- What pace (moderate = 4-5 activities/day, 60-90 min each)
- What interests (museums, food, waterfront)
- Constraints (timeframes, budget limits, meal requirements)

**Example Prompt Generated**:
```
Generate a complete day-by-day itinerary for a trip to Kingston, Canada.

**Trip Details:**
- Starting location: Downtown Kingston
- Location preference: downtown
- Dates: 2026-05-10 to 2026-05-12 (3 days)
- Hours per day: 8
- Budget: $900.00 total ($300.00/day) CAD
- Transportation: mixed

Pace: MODERATE
  - 4-5 activities per day
  - 60-90 minutes per activity
  - 15-minute buffers between activities
  - 60-minute lunch, 90-minute dinner

**Preferences:**
- Interests: museums, food, waterfront
- Dietary restrictions: None
- Group: not specified

Return the itinerary JSON now.
```

**Output**: String prompt ready for Gemini API

---

### Step 4: API Call - Call Gemini 2.5-Flash

**Code Location**: Lines 183-213  
**Method**: `generate_itinerary(preferences, request_id)` → calls `gemini_client.generate_content()`

**What happens**:
1. Calls Gemini 2.5-Flash asynchronously
2. Sends prompt + system instruction
3. Sets temperature: 0.7 (creative but consistent)
4. Max tokens: 8192 (enough for 7+ day itinerary)
5. Retry logic: 3 attempts with exponential backoff

**System Instruction** (Lines 32-212):
```
You are an expert Kingston, Ontario trip planner...

## Hard Constraints
- Every activity must have start/end times (HH:MM format)
- No overlapping events in same day
- Each day MUST have lunch + dinner
- Activity durations match pace parameters
- Daily costs cannot exceed budget
- First activity near starting location
- Last activity allows easy return

## Output Format
Return ONLY valid JSON (no markdown, no prose)
{
  "itinerary": {
    "days": [
      {
        "day": 1,
        "date": "2026-05-10",
        "morning_departure": {...},
        "activities": [...],
        "meals": [...],
        "evening_return": {...},
        "daily_budget_spent": 95.0
      }
    ]
  }
}
```

**Output**: Raw JSON string from Gemini

---

### Step 5: Parse Response - Extract structure

**Code Location**: Lines 405-449  
**Method**: `_parse_gemini_response(text, request_id)`

**What happens**:
1. Strips markdown code fences if present (```json ... ```)
2. Finds the JSON object in the response
3. Parses JSON into Python dict
4. Normalizes wrapper key ("itinerary")

**Example Raw Response from Gemini**:
```json
{
  "itinerary": {
    "option_name": "Moderate-Paced Kingston Explorer",
    "total_cost": 285.50,
    "activities_per_day_avg": 4.2,
    "total_travel_time_hours": 2.5,
    "days": [
      {
        "day": 1,
        "date": "2026-05-10",
        "morning_departure": {
          "time": "08:45",
          "from": "Downtown Kingston",
          "to": "Fort Henry",
          "travel_minutes": 15,
          "mode": "mixed"
        },
        "activities": [
          {
            "time_start": "09:00",
            "time_end": "10:15",
            "venue_name": "Fort Henry National Historic Site",
            "category": "museums",
            "cost": 22.0,
            "duration_reason": "Moderate pace — standard guided tour",
            "notes": "19th-century British military fortification"
          },
          {
            "time_start": "10:30",
            "time_end": "11:45",
            "venue_name": "Royal Military College Museum",
            "category": "museums",
            "cost": 0.0,
            "notes": "Military artifacts and history exhibits"
          }
        ],
        "meals": [
          {
            "meal_type": "lunch",
            "venue_name": "Dianne's Fish Shack & Smokehouse",
            "time": "12:00",
            "cost": 28.0
          },
          {
            "meal_type": "dinner",
            "venue_name": "Chez Piggy",
            "time": "18:00",
            "cost": 45.0
          }
        ],
        "evening_return": {
          "time": "19:30",
          "from": "Chez Piggy",
          "to": "Downtown Kingston",
          "travel_minutes": 5,
          "mode": "walking"
        },
        "daily_budget_allocated": 300.0,
        "daily_budget_spent": 95.0
      }
    ]
  }
}
```

**Output**: Parsed dict ready for object building

---

### Step 6: Build Objects - Create Itinerary dataclass

**Code Location**: Lines 451-538  
**Method**: `_build_itinerary_object(raw, prefs, request_id)`

**Creates**: Structured Python objects

**From JSON fields to Python objects**:
```python
JSON activity {
  "time_start": "09:00",
  "time_end": "10:15",
  "venue_name": "Fort Henry",
  "category": "museums",
  "cost": 22.0,
  "notes": "..."
}
↓
Activity(
  activity_id="trip_20260207_d1_a1",
  venue_name="Fort Henry",
  sequence=1,
  planned_start="09:00",
  planned_end="10:15",
  category="museums",
  estimated_cost=22.0,
  notes="..."
)

JSON meal {
  "meal_type": "lunch",
  "venue_name": "Dianne's Fish Shack",
  "time": "12:00",
  "cost": 28.0
}
↓
Meal(
  meal_type="lunch",
  venue_name="Dianne's Fish Shack",
  planned_time="12:00",
  estimated_cost=28.0
)

JSON day {
  "day": 1,
  "date": "2026-05-10",
  "activities": [...],
  "meals": [...],
  "daily_budget_allocated": 300.0,
  "daily_budget_spent": 95.0
}
↓
ItineraryDay(
  day_number=1,
  date="2026-05-10",
  activities=[Activity(...), Activity(...)],
  meals=[Meal(...), Meal(...)],
  daily_budget_allocated=300.0,
  daily_budget_spent=95.0,
  total_activities=2
)

All days ↓
Itinerary(
  trip_id="trip_20260207_a3f2b1c4",
  days=[ItineraryDay(...), ItineraryDay(...), ItineraryDay(...)],
  total_budget=900.0,
  total_spent=285.50,
  total_activities=9,
  activities_per_day_avg=4.2,
  total_travel_time_hours=2.5,
  pace="moderate"
)
```

**Output**: Itinerary object (from models/itinerary.py)

---

### Step 7: Feasibility Check - Validate constraints

**Code Location**: Lines 540-604  
**Method**: `_validate_feasibility(itinerary, prefs, request_id)`

**Checks each day**:
```python
✅ Day count matches expected duration
✅ Each day has activities
✅ Each day has 2+ meals (lunch + dinner)
✅ Daily budget not exceeded (10% tolerance)
✅ Activity count matches pace (4-5 for moderate)
✅ Total budget not exceeded (5% tolerance)
✅ User's interests are represented
```

**Example check**:
```python
# Day 1
activities = 4
meals = 2
budget_spent = $95.00
budget_allocated = $300.00

# Checks
4 activities >= 4 (min for moderate)? ✅ YES
4 activities <= 5 (max for moderate)? ✅ YES
2 meals >= 2? ✅ YES
95.00 <= 300.00 * 1.10 (330)? ✅ YES

# Result: FEASIBLE ✅
```

**Output**: 
```python
{
  "feasible": True,
  "issues": [],
  "warnings": []
}
```

If not feasible, raises `ItineraryGenerationError`

---

### Step 8: Return Itinerary

**Code Location**: Lines 213-220  
**Method**: `generate_itinerary()` returns Itinerary object

**What happens**:
1. Logs success with request ID
2. Returns complete Itinerary object
3. Ready for API response or storage

---

## 📁 File Relationships

### Imports (What this file depends on)

```python
# From other backend modules
from clients.gemini_client import GeminiClient, ExternalAPIError
from models.itinerary import (
    Itinerary,           # Complete itinerary container
    ItineraryDay,        # Single day in itinerary
    Activity,            # Single activity (museum, restaurant, etc.)
    Meal,                # Lunch or dinner
    TravelSegment,       # Transport between locations
)
from config.settings import settings
    # GEMINI_ITINERARY_TEMPERATURE = 0.7
    # GEMINI_ITINERARY_MAX_TOKENS = 8192
    # VALID_PACES = ["relaxed", "moderate", "packed"]
    # PACE_PARAMS = {...}  # Activity counts, durations per pace
    # MIN_DAILY_BUDGET = 50.0

# Standard library
import json              # Parse Gemini response
import asyncio          # Async API calls
from datetime import datetime, date  # Date validation
from typing import Dict, Any, List, Optional  # Type hints
```

### What uses this file

```
┌───────────────────────────────┐
│   User Request (API)          │
│   POST /api/generate-itinerary│
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│   Flask (backend/app.py)      │ (Step 1 - Route handler)
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│   ItineraryService            │ (This file - Steps 2-8)
│   generate_itinerary()        │
└──────────────┬────────────────┘
               │
       ┌───────┼───────┬─────────┐
       │               │         │
       ▼               ▼         ▼
    Gemini API    Settings   Models
                 (config)    (itinerary,
                             trip_prefs)
               │
               ▼
┌───────────────────────────────┐
│   Storage (future)            │
│   save_itinerary()            │
│   backend/storage/            │
└───────────────────────────────┘
       │
       ▼
┌───────────────────────────────┐
│   Database (MongoDB - future) │
│   trip_active_itineraries     │
└───────────────────────────────┘
```

---

## 📂 Output Files

### 1. **In-Memory Object** (Python)
**When**: Immediately after generation  
**Where**: In RAM during request processing  
**Format**: Itinerary dataclass instance  
**Contains**: All day/activity/meal data

```python
itinerary = Itinerary(
    trip_id="trip_20260207_a3f2b1c4",
    days=[...],
    total_budget=900.0,
    total_spent=285.50,
    ...
)
```

### 2. **JSON Response** (HTTP)
**When**: Returned to API caller  
**Where**: HTTP response body  
**Format**: JSON (via `itinerary.to_dict()`)  
**Location**: Sent to frontend or API client  
**Contains**: All structured data

```json
{
  "trip_id": "trip_20260207_a3f2b1c4",
  "days": [...],
  "total_budget": 900.0,
  "total_spent": 285.50,
  ...
}
```

### 3. **Saved JSON File** (Disk)
**When**: Called by demo script with `json.dump()`  
**Where**: Root project directory  
**File pattern**: `itinerary_trip_{timestamp}_{uuid}.json`  
**Example paths**:
```
./itinerary_trip_20260207_a3f2b1c4.json
./itinerary_trip_20260207_b2c3d1e5.json
```

**Format**: Pretty-printed JSON with 2-space indent

**Contains**:
```json
{
  "trip_id": "trip_20260207_a3f2b1c4",
  "itinerary_version": 1,
  "created_at": "2026-02-07T14:30:45.123456",
  "status": "draft",
  "days": [
    {
      "day_number": 1,
      "date": "2026-05-10",
      "activities": [...],
      "meals": [...],
      "daily_budget_allocated": 300.0,
      "daily_budget_spent": 95.0,
      ...
    },
    ...
  ],
  "total_budget": 900.0,
  "total_spent": 285.50,
  "total_activities": 9,
  "activities_per_day_avg": 4.2,
  "total_travel_time_hours": 2.5,
  "pace": "moderate"
}
```

### 4. **Potential Future Files**

**MongoDB Storage** (Phase 2):
```
Collection: trip_active_itineraries
Document:
{
  "_id": ObjectId(...),
  "trip_id": "trip_20260207_a3f2b1c4",
  "user_id": "user_123",
  "itinerary_data": {...},
  "created_at": ISODate("2026-02-07T14:30:45Z"),
  "status": "draft",
  "adaptation_count": 0
}
```

---

## 🔗 Related Files Explained

### 1. Models: `backend/models/itinerary.py`
**Purpose**: Define data structures  
**Contains**:
```python
@dataclass
class Activity:
    activity_id: str
    venue_name: str
    planned_start: str  # "09:00"
    planned_end: str     # "10:15"
    category: str        # "museums"
    cost: float          # 22.0
    notes: str
    status: str          # "pending"

@dataclass
class Meal:
    meal_type: str       # "lunch" or "dinner"
    venue_name: str
    planned_time: str    # "12:00"
    cost: float

@dataclass
class TravelSegment:
    mode: str            # "walking", "car", "transit"
    duration_minutes: int
    from_location: str
    to_location: str
    cost: float

@dataclass
class ItineraryDay:
    day_number: int
    date: str            # "2026-05-10"
    morning_departure: TravelSegment
    activities: List[Activity]
    meals: List[Meal]
    evening_return: TravelSegment
    daily_budget_allocated: float
    daily_budget_spent: float

@dataclass
class Itinerary:
    trip_id: str
    days: List[ItineraryDay]
    total_budget: float
    total_spent: float
    total_activities: int
    activities_per_day_avg: float
    total_travel_time_hours: float
    pace: str
    
    def to_dict(self):
        # Converts to JSON-serializable dict
```

### 2. Clients: `backend/clients/gemini_client.py`
**Purpose**: Call Gemini 2.5-Flash API  
**Used for**: API call in Step 4  
**Code**:
```python
response = await self.gemini_client.generate_content(
    prompt=prompt,
    system_instruction=GEMINI_ITINERARY_SYSTEM_INSTRUCTION,
    temperature=settings.GEMINI_ITINERARY_TEMPERATURE,
    max_tokens=settings.GEMINI_ITINERARY_MAX_TOKENS,
    request_id=request_id,
)
```

### 3. Config: `backend/config/settings.py`
**Purpose**: Store configuration  
**Used for**:
```python
settings.GEMINI_ITINERARY_TEMPERATURE  # 0.7
settings.GEMINI_ITINERARY_MAX_TOKENS   # 8192
settings.MIN_DAILY_BUDGET              # 50.0
settings.VALID_PACES                   # ["relaxed", "moderate", "packed"]
settings.PACE_PARAMS                   # Activity counts, durations per pace
```

### 4. Trip Preferences: `backend/models/trip_preferences.py`
**Purpose**: Input to itinerary generation  
**Used for**: Validation in Step 2  
**Contains**: 10 required fields + optional fields

---

## 🧪 Testing & Running

### Option 1: Demo Script
**File**: `demo_itinerary_generation.py`

```bash
python3 demo_itinerary_generation.py
```

**What it does**:
1. Creates 2 test trip preferences
2. Calls ItineraryService.generate_itinerary() for each
3. Prints formatted output
4. Saves JSON to files: `itinerary_trip_*.json`

**Time**: ~2 minutes (30-60s per itinerary)

**Output files**:
```
./itinerary_trip_20260207_a3f2b1c4.json  # 3-day moderate trip
./itinerary_trip_20260207_b2c3d1e5.json  # 5-day relaxed trip
```

### Option 2: Self-Test
**Built into the service file** (Lines 675-721)

```bash
cd backend
python3 -m services.itinerary_service
```

**What it does**:
1. Creates test preferences
2. Validates them
3. Builds prompt
4. Calls Gemini API
5. Parses response
6. Builds objects
7. Saves to `test_itinerary_output.json`

**Time**: 30-60 seconds

### Option 3: Via API (Future)
```bash
# Start server
python3 backend/app.py

# In another terminal
curl -X POST http://localhost:8000/api/generate-itinerary \
  -H "Content-Type: application/json" \
  -d @preferences.json | python3 -m json.tool
```

---

## 🚀 How Schedule is Created

### The Schedule Algorithm

Gemini (not this file) creates the schedule using the constraints:

**For Moderate Pace (4-5 activities/day, 60-90 min each)**:

```
08:00 - 08:45: Breakfast at hotel
08:45 - 09:00: Travel to Fort Henry (15 min)

09:00 - 10:15: Activity 1 - Fort Henry (75 min)
10:15 - 10:30: Buffer (15 min)

10:30 - 11:45: Activity 2 - Royal Military College Museum (75 min)
11:45 - 12:00: Buffer (15 min)

12:00 - 13:00: Lunch at Dianne's Fish Shack (60 min)
13:00 - 13:15: Buffer (15 min)

13:15 - 14:30: Activity 3 - Kingston City Hall (75 min)
14:30 - 14:45: Buffer (15 min)

14:45 - 16:00: Activity 4 - Kingston Waterfront Trail (75 min)
16:00 - 16:15: Buffer (15 min)

16:15 - 18:00: Free time/shopping (105 min)

18:00 - 19:30: Dinner at Chez Piggy (90 min)

19:30 - 19:35: Travel back downtown (5 min)
19:35 - onwards: Free time
```

**Gemini's decision process**:
1. Read interests: museums, food, waterfront
2. Select Kingston venues matching interests
3. Schedule first activity near downtown (Fort Henry 15 min away)
4. Add buffers between activities (15 min for moderate)
5. Calculate activity durations (60-90 min for moderate)
6. Include lunch at 12:00 (60 min for moderate)
7. Continue activities until 4-5 total
8. Schedule dinner at 18:00 (90 min for moderate)
9. Last activity near return route
10. Total cost per day <= $300 (budget)

---

## 💾 Data Storage Flow

```
Trip Preferences (JSON)
    ↓
[Python dict]
    ↓
ItineraryService.generate_itinerary()
    ↓
[Itinerary object in RAM]
    ↓
itinerary.to_dict() [convert to dict]
    ↓
json.dumps() [convert to JSON string]
    ↓
json.dump(file) [save to file]
    ↓
itinerary_trip_*.json [saved to disk]
```

---

## ⚠️ Current Issues

### Import Bugs (Blocking)
**Files affected**:
- `backend/clients/gemini_client.py` lines 55, 91
- `backend/services/itinerary_service.py` lines 22, 23, 30

**Issue**: Uses `from backend.clients...` instead of `from clients...`

**Fix**: Change import paths to be relative to `backend/` directory

### Missing Endpoint
**Issue**: No `/api/generate-itinerary` endpoint in Flask

**Fix**: Add to `backend/app.py`:
```python
@app.route('/api/generate-itinerary', methods=['POST'])
async def generate_itinerary():
    """Generate itinerary from preferences."""
    try:
        data = request.get_json()
        preferences = data.get('preferences')
        
        service = ItineraryService()
        itinerary = await service.generate_itinerary(preferences, request_id="req-001")
        
        return jsonify({
            'success': True,
            'itinerary': itinerary.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

## 📊 Summary Table

| Aspect | Details |
|--------|---------|
| **Purpose** | Generate day-by-day travel itinerary |
| **Input** | Trip preferences (dict with 10 fields) |
| **Output** | Itinerary object + JSON file |
| **Processing** | Validate → Build prompt → Call Gemini → Parse → Build objects → Validate |
| **Time** | 30-60 seconds |
| **Gemini Model** | gemini-2.5-flash |
| **Cost** | ~$0.10 per itinerary |
| **Dependencies** | GeminiClient, models, settings |
| **Related files** | itinerary.py, trip_preferences.py, gemini_client.py |
| **Output location** | RAM (Itinerary object) + HTTP response + optional JSON file |
| **Testing** | `demo_itinerary_generation.py` or self-test in file |
| **Status** | ✅ Implemented, ⚠️ Has import bugs |

---

**This service is the core of itinerary generation!** Once the import bugs are fixed, it will be fully functional.
