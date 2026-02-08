# MonVoyage Backend - Analysis & Action Items

**Generated:** February 7, 2026  
**Branch:** vietbui  
**Status:** Backend 75% Complete - Import bugs FIXED, Gemini is primary LLM

---

## 1. Project Workflow Overview

### Data Flow
```
User Input → NLP Extraction → Validation → Storage → Itinerary Generation
```

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│ backend/app.py (Flask server)                                │
│ - Initializes NLPExtractionService                          │
│ - Serves frontend & API routes                              │
│ - Port 8000                                                  │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ API Endpoints (backend/app.py - routes not separated yet)   │
│ - GET  /api/health                                          │
│ - POST /api/extract    (initial extraction)                 │
│ - POST /api/refine     (update with more info)              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ services/nlp_extraction_service.py                          │
│ - extract_preferences()     - Parses natural language       │
│ - refine_preferences()      - Updates existing prefs        │
│ - validate_preferences()    - Checks completeness           │
│ - save_preferences_to_file() - Persists to JSON            │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ clients/gemini_client.py (Primary - ✅ WORKING)             │
│ - Async Gemini API wrapper with retry logic                │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────────┐
│ clients/groq_client.py (Fallback)                           │
│ - Synchronous Groq API wrapper                              │
└──────────────────┬──────────────────┬───────────────────────┘
                   │                  │
                   ▼                  ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│ models/trip_preferences  │  │ services/itinerary_service   │
│ - TripPreferences schema │  │ - generate_itinerary()       │
│ - Validation & mapping   │  │ - ✅ WORKING                 │
└──────────────────────────┘  └──────────────────────────────┘
```

### Key Modules & Responsibilities

| Module | Responsibility | Status | Key Files |
|--------|----------------|--------|-----------|
| **config/** | Environment variables, settings, validation | ✅ Working | `settings.py` |
| **clients/** | External API wrappers (Gemini, Groq) | ✅ Working | `gemini_client.py`, `groq_client.py` |
| **models/** | Data structures & schemas | ✅ Working | `trip_preferences.py`, `itinerary.py` |
| **services/** | Business logic (extraction, generation) | ✅ Working | `nlp_extraction_service.py`, `itinerary_service.py` |
| **routes/** | API endpoints | ❌ Empty - inline in app.py | `trip_routes.py` |
| **controllers/** | Request handlers | ❌ Empty - inline in app.py | `trip_controller.py` |
| **storage/** | Persistence layer | ❌ Empty - file-based for now | `trip_json_repo.py`, `itinerary_json_repo.py` |

---

## 2. How to Run Locally

### Prerequisites
```bash
# Ensure Python 3.8+ is installed
python3 --version  # 3.11.5 confirmed in your env

# Virtual environment already activated
source venv/bin/activate
```

### Commands Reference

| Task | Command | Expected Output |
|------|---------|-----------------|
| **Check configuration** | `python3 backend/diagnose.py` | ✅ ALL CHECKS PASSED |
| **Start dev server** | `python3 backend/app.py` | Server on http://127.0.0.1:8000 |
| **Run NLP demo** | `python3 demo_nlp_extraction.py` | Shows extraction examples |
| **Run itinerary demo** | `python3 demo_itinerary_generation.py` | ✅ Generates itineraries |
| **Test API health** | `curl http://localhost:8000/api/health \| python3 -m json.tool` | Health check JSON |
| **Test extraction** | `curl -X POST http://localhost:8000/api/extract -H "Content-Type: application/json" -d '{"user_input": "Kingston May 10-12, $900, museums"}' \| python3 -m json.tool` | Extracted preferences |

### Environment Variables

**Location:** `backend/.env` (already configured ✅)

```env
# Primary LLM
GEMINI_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.5-flash
EXTRACTION_TEMPERATURE=0.2
ITINERARY_TEMPERATURE=0.7
EXTRACTION_MAX_TOKENS=2048
ITINERARY_MAX_TOKENS=8192

# Fallback LLM
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.3-70b-versatile

# App config
PORT=8000
HOST=127.0.0.1
DEBUG=True
```

---

## 3. Resolved Issues

### ✅ **FIXED: Gemini Client Import Failure** (Fixed 2026-02-07)

**What was wrong:** The code used absolute imports (`from backend.config.settings import settings`) instead of short imports. Since `app.py` adds only `backend/` to `sys.path`, the `backend` prefix caused `ModuleNotFoundError`.

**Files Fixed:**

| File | Lines | Before (broken) | After (fixed) |
|------|-------|-----------------|---------------|
| `backend/clients/gemini_client.py` | 55, 91 | `from backend.config.settings import settings` | `from config.settings import settings` |
| `backend/services/itinerary_service.py` | 22 | `from backend.clients.gemini_client import...` | `from clients.gemini_client import...` |
| `backend/services/itinerary_service.py` | 23-28 | `from backend.models.itinerary import...` | `from models.itinerary import...` |
| `backend/services/itinerary_service.py` | 30 | `from backend.config.settings import settings` | `from config.settings import settings` |

**Expected startup output after fix:**
```bash
$ python3 backend/app.py
✅ NLP Extraction Service initialized successfully
📍 Using Gemini API (Primary): gemini-2.5-flash
🌐 Starting server on http://127.0.0.1:8000
```

---

## 4. Priority Action Items

### ✅ COMPLETED: Import Bug Fixes (Fixed 2026-02-07)

- ✅ Gemini client imports fixed (`gemini_client.py` lines 55, 91)
- ✅ Itinerary service imports fixed (`itinerary_service.py` lines 22, 23-28, 30)
- ✅ Gemini now loads as primary LLM
- ✅ Itinerary generation service is functional
- ❌ `/api/generate-itinerary` endpoint still doesn't exist (see Task 4)

### 🔴 HIGH PRIORITY (Next Up)

#### Task 3: Test Itinerary Generation End-to-End
**Prerequisite:** Import fixes complete ✅

---

## Testing Itinerary Service: Complete Guide

### What is the Itinerary Service?

The Itinerary Service (`backend/services/itinerary_service.py`) takes validated trip preferences and generates a complete day-by-day itinerary with:
- ✅ Specific times for each activity (HH:MM format)
- ✅ Venue names with descriptions
- ✅ Cost tracking (activities + meals)
- ✅ Transportation between locations
- ✅ Meal planning (lunch + dinner daily)
- ✅ Feasibility validation

### How It Works

**Flow:**
```
Trip Preferences (from user input)
       ↓
[Validate] - Check all 10 required fields
       ↓
[Build Prompt] - Create context for Gemini
       ↓
[Call Gemini 2.5-Flash API] - Generate day-by-day schedule
       ↓
[Parse JSON Response] - Extract structured itinerary
       ↓
[Feasibility Check] - Verify pace, budget, day count
       ↓
Complete Itinerary JSON
```

**Input Example:**
```python
preferences = {
    "city": "Kingston",
    "country": "Canada",
    "start_date": "2026-05-10",
    "end_date": "2026-05-12",
    "duration_days": 3,
    "budget": 900.0,
    "budget_currency": "CAD",
    "interests": ["museums", "food", "waterfront"],
    "pace": "moderate",
    "location_preference": "downtown"
}
```

**Output Example:**
```json
{
  "trip_id": "trip_20260207_a3f2b1c4",
  "days": [
    {
      "day": 1,
      "date": "2026-05-10",
      "activities": [
        {
          "time_start": "09:00",
          "time_end": "10:15",
          "venue_name": "Fort Henry National Historic Site",
          "category": "museums",
          "cost": 22.0
        },
        {
          "time_start": "12:00",
          "time_end": "13:00",
          "meal_type": "lunch",
          "venue_name": "Dianne's Fish Shack",
          "cost": 28.0
        }
      ],
      "daily_budget_spent": 95.0,
      "daily_budget_allocated": 300.0
    }
  ],
  "total_cost": 285.0,
  "activities_per_day_avg": 4.2
}
```

### Step 1: Import Fixes ✅ DONE

All import bugs have been fixed (2026-02-07). Gemini loads as primary LLM.

### Step 2: Run the Demo Script

**Option A: Simple Demo (Recommended)**
```bash
cd /Users/vietbui/Desktop/monVoyage/MonVoyage
python3 demo_itinerary_generation.py
```

**What you'll see:**
```
===============================================================================
  ITINERARY GENERATION SERVICE - DEMO
===============================================================================

[1] Initializing Itinerary Generation Service...
✅ Service initialized (uses Gemini API)

========================================================================
EXAMPLE 1: 3-Day Moderate Pace Trip
========================================================================

Input Preferences:
{
  "city": "Kingston",
  "country": "Canada",
  "start_date": "2026-05-10",
  "end_date": "2026-05-12",
  "duration_days": 3,
  "budget": 900.0,
  "interests": ["museums", "food", "waterfront"],
  "pace": "moderate",
  "location_preference": "downtown"
}

[Generating itinerary... this may take 30-60 seconds]

✅ Itinerary Generated!
   Trip ID: trip_20260207_a3f2b1c4
   Days: 3
   Total Activities: 12
   Avg Activities/Day: 4.0
   Total Cost: $285.00 / $900.00
   Total Travel Time: 2.5 hours

📅 Day 1 - 2026-05-10
   Budget: $95.00 / $300.00

   Morning Departure:
   └─ From: Downtown Kingston
   └─ To: Fort Henry
   └─ Travel: 15 min by mixed

   Activities:
   • 09:00-10:15: Fort Henry National Historic Site
     └─ Category: museums | Cost: $22
     └─ 19th-century British military fortification
   • 10:30-11:45: Royal Military College Museum
     └─ Category: museums | Cost: $0
     └─ Military artifacts and history exhibits
   • 13:15-14:30: Kingston City Hall
     └─ Category: museums | Cost: $0
     └─ National Historic Site with stunning architecture
   • 14:45-16:00: Kingston Waterfront Trail
     └─ Category: food | Cost: $0
     └─ Scenic waterfront walk from City Park to Breakwater Park

   Meals:
   • 12:00: lunch at Dianne's Fish Shack & Smokehouse ($28)
   • 18:00: dinner at Chez Piggy ($45)

   Evening Return:
   └─ From: Chez Piggy
   └─ To: Downtown Kingston
   └─ Travel: 5 min by walking

💾 Full itinerary saved to: itinerary_trip_20260207_a3f2b1c4.json
```

**Timing:**
- Example 1 (3-day trip): ~30-45 seconds
- Example 2 (5-day trip): ~45-60 seconds
- Total runtime: ~2 minutes

**Output Files:**
- `itinerary_trip_20260207_a3f2b1c4.json` - 3-day itinerary
- `itinerary_trip_20260207_b2c3d1e5.json` - 5-day itinerary

---

### Step 4: Test via API (After Adding Endpoint)

Once the endpoint is created, test like this:

**Start server:**
```bash
python3 backend/app.py
```

**In another terminal:**
```bash
# Save preferences to file first
cat > /tmp/preferences.json << 'EOF'
{
  "city": "Kingston",
  "country": "Canada",
  "start_date": "2026-07-15",
  "end_date": "2026-07-17",
  "duration_days": 3,
  "budget": 750.0,
  "budget_currency": "CAD",
  "interests": ["Food and Beverage", "Culture and History"],
  "pace": "relaxed",
  "location_preference": "downtown"
}
EOF

# Call the API
curl -X POST http://localhost:8000/api/generate-itinerary \
  -H "Content-Type: application/json" \
  -d @/tmp/preferences.json | python3 -m json.tool
```

**Expected Response:**
```json
{
  "success": true,
  "trip_id": "trip_20260207_xyz123",
  "itinerary": {
    "days": [...],
    "total_activities": 9,
    "total_cost": 245.50
  },
  "feasibility": {
    "feasible": true,
    "issues": [],
    "warnings": []
  }
}
```

---

### Step 5: Test Self-Test Built Into Service

**Run the service's built-in test:**
```bash
cd /Users/vietbui/Desktop/monVoyage/MonVoyage/backend
python3 -m services.itinerary_service
```

**What it does:**
1. Creates test trip preferences
2. Validates them
3. Builds the Gemini prompt
4. Calls Gemini API
5. Parses and validates the response
6. Saves output to `test_itinerary_output.json`

**Output:**
```
========================================================================
  ITINERARY SERVICE — SELF-TEST
========================================================================

[INPUT]
{
  "city": "Kingston",
  "country": "Canada",
  "start_date": "2026-05-10",
  "end_date": "2026-05-17",
  "duration_days": 7,
  "budget": 2500.0,
  "interests": ["museums", "food tours", "historic landmarks", ...],
  "pace": "moderate",
  "location_preference": "City center near public transportation"
}

[1] Validating preferences ...
    ✓ Daily budget: $357.14
    ✓ Duration: 7 days
    ✓ Pace: moderate

[2] Building Gemini prompt ...
    ✓ Prompt length: 2847 chars

[3] Calling Gemini API (may take 30-60 s) ...

    ✓ Itinerary generated!
      Days:       7
      Activities: 32
      Avg/day:    4.6
      Cost:       $2345.50 / $2500.00

    Day 1 — 2026-05-10
      09:00-10:15  Fort Henry  ($22.00)
      10:30-11:45  Royal Military College Museum  ($0.00)
      13:15-14:30  Kingston City Hall  ($0.00)
      14:45-16:00  Kingston Waterfront Trail  ($0.00)

    ✓ Saved full output to test_itinerary_output.json

========================================================================
  FULL SELF-TEST PASSED ✓
========================================================================
```

---

### Troubleshooting

**Error: "No module named 'clients'"**
```
→ Import fixes have been applied. If you still see this, ensure you're running
  from the project root: python3 backend/app.py
```

**Error: "GEMINI_KEY is required"**
```
→ Check that GEMINI_KEY is set in backend/.env
→ Run: python3 backend/diagnose.py
```

**Error: "RuntimeError: asyncio.get_event_loop()"**
```
→ This is a known issue with async/sync mixing
→ Make sure you're using Python 3.11.5 (which you are)
```

**Process takes > 90 seconds**
```
→ Gemini API is slow (30-60s per request is normal)
→ Check your internet connection
→ Check Gemini API status at https://ai.google.dev/
```

**Itinerary is missing activities**
```
→ Interests might not match Kingston venues
→ Try adding more common interests: "museums", "food", "waterfront"
```

**Budget exceeded in output**
```
→ 10% tolerance is allowed per day
→ Check the feasibility report in the output
→ Increase total budget if activities are too expensive
```

---

### 🟡 MEDIUM PRIORITY (Next Up)

#### Task 4: Add Itinerary Generation API Endpoint
**Prerequisite:** Import fixes complete ✅
**Commands:**
```bash
# Test via demo script
python3 demo_itinerary_generation.py

# Test via API (once endpoint exists)
curl -X POST http://localhost:8000/api/generate-itinerary \
  -H "Content-Type: application/json" \
  -d @backend/data/trip_requests/trip_kingston_*.json
```

**Expected Output:**
- 2 complete itineraries generated (3-day moderate, 5-day relaxed)
- JSON files saved to project root
- Each itinerary includes: daily schedule, activities, meals, costs, travel times

**Estimated Time:** 10 minutes testing

---

#### Task 5: Add Itinerary Generation API Endpoint
**File:** `backend/app.py` (or move to `backend/routes/trip_routes.py`)  
**Endpoint:** `POST /api/generate-itinerary`  
**Request Body:**
```json
{
  "preferences": {
    "city": "Kingston",
    "country": "Canada",
    "start_date": "2026-05-10",
    "end_date": "2026-05-12",
    "duration_days": 3,
    "budget": 900.0,
    "budget_currency": "CAD",
    "interests": ["Culture and History", "Food and Beverage"],
    "pace": "moderate",
    "location_preference": "downtown"
  }
}
```

**Implementation:**
```python
@app.route('/api/generate-itinerary', methods=['POST'])
async def generate_itinerary():
    """Generate day-by-day itinerary from trip preferences."""
    # 1. Validate preferences
    # 2. Call ItineraryService.generate_itinerary()
    # 3. Save to storage
    # 4. Return itinerary JSON
```

**Estimated Time:** 30 minutes

---

### 🟢 LOW PRIORITY (Future Iterations)

#### Task 6: Separate Routes from app.py
**Goal:** Move API endpoints to `backend/routes/trip_routes.py`  
**Current State:** All routes defined inline in `backend/app.py`  
**Target State:** Blueprint pattern with modular routes

**Changes:**
1. Create Flask Blueprint in `trip_routes.py`
2. Move `/api/extract`, `/api/refine`, `/api/generate-itinerary` to blueprint
3. Register blueprint in `app.py`

**Estimated Time:** 20 minutes

---

#### Task 7: Implement Controllers
**Goal:** Extract business logic from routes into `backend/controllers/trip_controller.py`  
**Pattern:**
```python
# controllers/trip_controller.py
class TripController:
    def extract_preferences(self, user_input: str) -> dict:
        # Business logic here
        
    def refine_preferences(self, preferences: dict, additional: str) -> dict:
        # Business logic here
```

**Estimated Time:** 30 minutes

---

#### Task 8: MongoDB Integration
**Goal:** Replace file-based storage with MongoDB  
**Files to implement:**
- `backend/storage/trip_json_repo.py`
- `backend/storage/itinerary_json_repo.py`

**Collections (per CLAUDE_EMBEDDED.md):**
- `user_trip_requests` - Trip preferences
- `trip_active_itineraries` - Generated itineraries
- `kingston_venues` - Venue database
- `trip_budget_state` - Budget tracking
- `scraped_venue_data` - Web scraping results
- `venue_change_alerts` - Change detection
- `kingston_weather_forecast` - Weather data

**Estimated Time:** 2-3 hours

---

## 5. Backend File Inventory

### ✅ Implemented & Working

**Configuration**
- `backend/config/settings.py` (135 lines) - Environment config, validation, constants

**Clients**
- `backend/clients/groq_client.py` (142 lines) - Groq API wrapper ✅ Working
- `backend/clients/gemini_client.py` (156 lines) - Gemini API wrapper ✅ Working (import bug fixed)

**Models**
- `backend/models/trip_preferences.py` (293 lines) - Preferences schema with validation
- `backend/models/itinerary.py` (167 lines) - Itinerary data structures

**Services**
- `backend/services/nlp_extraction_service.py` (632 lines) - NLP extraction ✅ Working
- `backend/services/itinerary_service.py` (721 lines) - Itinerary generation ✅ Working (import bug fixed)

**Utilities**
- `backend/utils/id_generator.py` (26 lines) - UUID generation

**Application**
- `backend/app.py` (218 lines) - Flask server, all routes inline

**Scripts**
- `backend/diagnose.py` (76 lines) - Configuration checker
- `demo_nlp_extraction.py` (118 lines) - NLP examples
- `demo_itinerary_generation.py` (165 lines) - Itinerary examples

---

### ❌ Empty/Stub Files (Need Implementation)

**Routes**
- `backend/routes/trip_routes.py` (0 lines) - Should contain `/api/*` endpoints

**Controllers**
- `backend/controllers/trip_controller.py` (0 lines) - Should contain business logic handlers

**Storage**
- `backend/storage/trip_json_repo.py` (0 lines) - Should implement trip CRUD
- `backend/storage/itinerary_json_repo.py` (0 lines) - Should implement itinerary CRUD

---

### 📁 Data Storage (Current: File-Based)

**Location:** `backend/data/trip_requests/`  
**Format:** JSON files with naming pattern: `trip_{city}_{timestamp}.json`  
**Status:** Working for MVP, needs MongoDB migration

---

## 6. Testing Checklist

### Pre-Fix (Before 2026-02-07)
- [x] `python3 backend/diagnose.py` - ✅ Passes
- [x] `python3 backend/app.py` - ⚠️ Started with Groq fallback (now fixed)
- [x] NLP extraction via web UI - ✅ Works
- [x] NLP extraction via API - ✅ Works
- [x] Itinerary generation - ✅ Fixed (was failing due to import error)

### Post-Fix (After 2026-02-07)
- [x] `python3 backend/app.py` - ✅ Shows "Using Gemini API (Primary)"
- [x] `python3 demo_nlp_extraction.py` - ✅ Completes with Gemini
- [x] `python3 demo_itinerary_generation.py` - ✅ Generates itineraries
- [ ] Web UI itinerary generation - Needs `/api/generate-itinerary` endpoint

---

## 7. Architecture Gaps (Per Requirements)

According to `CLAUDE_EMBEDDED.md`, these features are **mandatory for MVP** but **not yet implemented:**

### Missing MVP Features

| Feature | Status | Priority | Estimated Effort |
|---------|--------|----------|------------------|
| MongoDB Integration | ❌ Not started | High | 2-3 hours |
| Multi-Modal Transportation | ❌ Not started | Medium | 2 hours |
| Real-Time Weather Tracking | ❌ Not started | Medium | 3 hours |
| Real-Time Budget Tracking | ❌ Not started | Low | 1 hour |
| Real-Time Schedule Adaptation | ❌ Not started | Low | 4 hours |
| Web Scraping (Airflow) | ❌ Not started | Low | 6 hours |

**Current Phase:** Phase 1 (NLP Extraction) - ✅ Complete
**Next Phase:** Phase 2 (Itinerary Generation + MongoDB) - 60% complete (service done, needs API endpoint + MongoDB)
**MVP Completeness:** ~45% overall

---

## 8. Quick Wins Summary

### ✅ Completed Quick Wins (2026-02-07)

1. ~~**Fix Gemini imports** - 2 files, 5 lines total~~ ✅ DONE
2. **Test itinerary generation** - Run `python3 demo_itinerary_generation.py`
3. **Verify Gemini is primary LLM** - Run `python3 backend/app.py`, check startup logs

### ⏭️ Next Session Goals

1. Add `/api/generate-itinerary` endpoint
2. Test end-to-end: User input → Extraction → Validation → Itinerary generation
3. Start MongoDB integration planning

---

## 9. Known Issues Register

| ID | Issue | Impact | Status | Fix ETA |
|----|-------|--------|--------|---------|
| #001 | ~~Gemini client import bug~~ | ~~Can't use primary LLM~~ | ✅ Fixed | Done |
| #002 | ~~Itinerary service import bug~~ | ~~Can't generate itineraries~~ | ✅ Fixed | Done |
| #003 | Routes not separated | Technical debt | 🟡 Medium | 20 min |
| #004 | Controllers empty | Technical debt | 🟡 Medium | 30 min |
| #005 | Storage layer empty | Can't scale beyond file system | 🟢 Low | 2-3 hours |
| #006 | No itinerary API endpoint | Can't generate via API | 🟡 Medium | 30 min |

---

## 10. Documentation Status

### ✅ Complete Documentation
- `QUICK_START.md` - User guide for running the system
- `USAGE_GUIDE.md` - Comprehensive API & testing guide
- `CLAUDE.md` - Project context & architecture
- `backend/CLAUDE_EMBEDDED.md` - Backend-specific rules
- `README_NLP_SETUP.md` - NLP setup instructions
- Individual README files in each `backend/` subdirectory

### ⚠️ Needs Update
- `README.md` (root) - Currently empty
- API documentation - No OpenAPI/Swagger spec

---

## Contact & Next Steps

**Recommended Action:** Import bugs are fixed. Next step is adding the `/api/generate-itinerary` endpoint and testing end-to-end itinerary generation.

**Estimated Time to Full MVP:** 15-20 hours (API endpoint, MongoDB, weather, transportation features)

---

*Analysis generated on February 7, 2026. Import bugs fixed on February 7, 2026.*
