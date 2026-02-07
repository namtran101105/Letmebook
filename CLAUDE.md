# Kingston Trip Planner - Project Context for Claude

## Project Overview

The Kingston Trip Planner is a real-time, AI-powered itinerary engine that generates feasible travel itineraries for Kingston, Ontario visitors. This is an MVP being built for a 2-week hackathon demonstration.

**Current Status**: Phase 1 Complete, Phase 2 (Itinerary Generation) In Progress
**Team Size**: 3 developers
**Timeline**: 14 days

## Project Goals

Build a working prototype that demonstrates:
1. AI-powered itinerary generation from natural language user input
2. Real-time travel planning with multi-modal transportation
3. Dynamic budget tracking and schedule adaptation
4. Weather-aware activity recommendations
5. Automated venue data collection with change detection

## Architecture Overview

### Current Implementation (Phase 1 Complete)

**Backend**: Flask-based REST API with layered architecture
- `routes/` - API endpoints (HTTP layer)
- `controllers/` - Request handlers
- `services/` - Business logic (NLP extraction, itinerary generation)
- `clients/` - External API wrappers (Gemini, Groq, Google Maps, Weather)
- `models/` - Data structures (TripPreferences, Itinerary)
- `config/` - Configuration management
- `utils/` - Helper functions

**Frontend**: Single-page HTML/CSS/JS chatbot interface
- Split-panel design: Chat interface | Extracted preferences display
- Real-time preference extraction and validation
- Support for refinement (updating preferences with additional input)

**Database**: MongoDB (planned for Phase 2)

## Technology Stack

### Core Technologies
- **Backend Framework**: Flask 3.0.0 with Flask-CORS
- **AI/NLP**: Gemini API (primary, via google-genai SDK) / Groq API (fallback, llama-3.3-70b-versatile model)
- **Language**: Python 3.8+
- **Database**: MongoDB (planned)
- **APIs**: Google Maps API, Weather API (planned)
- **Task Scheduling**: Apache Airflow (planned)

### Dependencies
```
flask==3.0.0
flask-cors==4.0.0
google-genai>=1.0.0
groq>=0.13.0
httpx>=0.27.0
python-dotenv==1.0.0
python-dateutil==2.8.2
pytest==7.4.3
pytest-cov==4.1.0
black==23.12.1
flake8==7.0.0
```

## Data Models

### TripPreferences Schema

#### Required Fields (10):
```python
@dataclass
class TripPreferences:
    # Location
    city: str                           # REQUIRED
    country: str                        # REQUIRED
    location_preference: str            # REQUIRED - e.g., "downtown", "near nature"

    # Dates
    start_date: str                     # REQUIRED - YYYY-MM-DD
    end_date: str                       # REQUIRED - YYYY-MM-DD
    duration_days: int                  # REQUIRED - must match date range

    # Budget
    budget: float                       # REQUIRED - daily >= $50
    budget_currency: str                # REQUIRED

    # Preferences
    interests: List[str]                # REQUIRED - min 1 category
    pace: str                           # REQUIRED - "relaxed"|"moderate"|"packed"
```

#### Optional Fields (with defaults):
```python
    # Defaulted optional fields
    starting_location: Optional[str] = None   # Default: from location_preference
    hours_per_day: int = 8                     # Default: 8
    transportation_modes: List[str] = None     # Default: ["mixed"]

    # Other optional fields
    group_size: Optional[int] = None
    group_type: Optional[str] = None
    children_ages: Optional[List[int]] = None
    dietary_restrictions: Optional[List[str]] = None
    accessibility_needs: Optional[List[str]] = None
    weather_tolerance: Optional[str] = None
    must_see_venues: Optional[List[str]] = None
    must_avoid_venues: Optional[List[str]] = None
```

## Critical Requirements & Validation Rules

### Phase 1 (Current): Information Collection

**Required Inputs (10 fields)** (cannot generate itinerary without these):
1. **City** - Destination city (e.g., Kingston)
2. **Country** - Destination country (e.g., Canada)
3. **Start date** - Trip start date (YYYY-MM-DD)
4. **End date** - Trip end date (YYYY-MM-DD)
5. **Duration days** - Number of days (must match date range)
6. **Budget** - Total OR daily budget (minimum $50/day for meals + activities)
7. **Budget currency** - Currency code (default: CAD)
8. **Interests** - At least ONE category (history, food, waterfront, nature, arts, museums, shopping, nightlife)
9. **Pace preference** - Relaxed, moderate, or packed schedule
10. **Location preference** - Area preference (e.g., "downtown", "near waterfront")

**Optional Inputs** (with defaults):
- **Starting location** - User's base in Kingston (default: derived from location_preference)
- **Hours per day** - Hours available for activities (default: 8)
- **Transportation mode** - car, transit, walking, mixed (default: ["mixed"])
- **Group details** - size, type, children ages
- **Dietary restrictions** - List of dietary needs
- **Accessibility needs** - List of accessibility requirements
- **Weather tolerance** - Weather sensitivity level
- **Must-see/must-avoid venues** - Venue preferences

**Validation Rules**:
- **Budget**: Daily budget MUST BE ≥ $50 (for two meals + activities)
  - Reject if < $50
  - Warn if $50-70 (tight budget)
  - Confirm if ≥ $70
- **Dates**: Start date must be today or future, end date must be after start
- **Interests**: At least 1 required, optimal 2-4, max 6
- **Pace**: Must be one of "relaxed", "moderate", or "packed"

**Pace-Specific Parameters**:
- **Relaxed**: 2-3 activities/day, 90-120 min/activity, 20-min buffers, 90+ min meals
- **Moderate**: 4-5 activities/day, 60-90 min/activity, 15-min buffers, 60-90 min meals
- **Packed**: 6+ activities/day, 30-60 min/activity, 5-min buffers, 45-60 min meals

### Phase 2 (Planned): MongoDB Collections

**Collections to implement**:
1. `user_trip_requests` - User constraints and preferences
2. `kingston_venues` - Master database of attractions/restaurants
3. `trip_active_itineraries` - Generated itineraries with execution tracking
4. `trip_budget_state` - Real-time budget tracking
5. `scraped_venue_data` - Raw scraped content and change detection
6. `venue_change_alerts` - Detected changes from web scraping
7. `kingston_weather_forecast` - Weather forecasts for planning

## API Endpoints (Current Implementation)

### Health Check
```
GET /api/health
Response: {
  "status": "healthy",
  "service": "Kingston Trip Planner",
  "primary_llm": "gemini",
  "fallback_llm": "groq",
  "nlp_service_ready": boolean,
  "error": string | null
}
```

### Extract Preferences (Initial)
```
POST /api/extract
Request: {
  "user_input": "I want to visit Kingston next weekend with my family..."
}
Response: {
  "success": boolean,
  "preferences": TripPreferences,
  "validation": {
    "valid": boolean,
    "issues": string[],
    "warnings": string[],
    "completeness_score": float (0.0-1.0)
  }
}
```

### Refine Preferences (Follow-up)
```
POST /api/refine
Request: {
  "preferences": {...},
  "additional_input": "I'm vegetarian and want to see Fort Henry"
}
Response: {
  "success": boolean,
  "preferences": TripPreferences,
  "validation": {...}
}
```

## NLP Extraction Service

### System Instruction
The Gemini API (primary) / Groq API (fallback) uses a system instruction that:
- Extracts structured information from natural language
- Focuses on: city, country, dates, duration_days, budget, budget_currency, interests, pace, location_preference
- Uses conservative extraction (only explicit/implied info)
- Returns valid JSON only

### Extraction Process
1. User provides natural language input
2. Service builds extraction prompt with JSON schema
3. Gemini API (primary) or Groq API (fallback) extracts structured data
4. Service validates and creates TripPreferences object
5. Validation checks completeness and flags issues

### JSON Mode
Uses structured output / JSON mode to ensure structured output from the LLM API.

## Development Guidelines

### Code Style
- Use **Black** for code formatting
- Use **Flake8** for linting
- Follow PEP 8 conventions
- Type hints for function parameters and returns

### Error Handling
- Never guess or make assumptions - ask user for clarification
- Validate all user inputs against minimum requirements
- Provide clear error messages with actionable guidance
- Log errors with full traceback for debugging

### Security
- Never commit API keys (use .env files)
- Validate and sanitize all user inputs
- Use environment variables for sensitive configuration
- Follow OWASP security best practices

### Testing
- Write unit tests for core business logic
- Test NLP extraction with various input formats
- Validate edge cases (missing data, invalid formats)
- Test API endpoints with different scenarios

## Current File Structure

```
MonVoyage/
├── backend/
│   ├── app.py                          # Flask application entry point (port 8000)
│   ├── config/
│   │   └── settings.py                 # Configuration management (Gemini + Groq config)
│   ├── models/
│   │   ├── trip_preferences.py         # TripPreferences dataclass (272 lines)
│   │   └── itinerary.py               # Itinerary data structures (159 lines)
│   ├── services/
│   │   ├── nlp_extraction_service.py   # NLP extraction logic (632 lines) ✅
│   │   └── itinerary_service.py        # Itinerary generation via Gemini (721 lines) ✅
│   ├── clients/
│   │   ├── gemini_client.py            # Gemini API wrapper (primary) ✅
│   │   └── groq_client.py             # Groq API wrapper (fallback) ✅
│   ├── routes/
│   │   └── trip_routes.py              # Route definitions (empty stub - TODO)
│   ├── controllers/
│   │   └── trip_controller.py          # Business logic handlers (empty stub - TODO)
│   ├── storage/
│   │   ├── trip_json_repo.py           # Trip persistence (empty stub - TODO)
│   │   └── itinerary_json_repo.py      # Itinerary persistence (empty stub - TODO)
│   ├── utils/
│   │   └── id_generator.py             # Trip/itinerary ID generation
│   ├── data/
│   │   └── trip_requests/              # Saved trip preference JSON files
│   ├── requirements.txt                # Python dependencies
│   ├── .env                            # Environment variables (not in git)
│   ├── .env.example                    # Environment template
│   ├── diagnose.py                     # Setup diagnostic script
│   ├── test_imports.py                 # Import verification script
│   └── CLAUDE_EMBEDDED.md             # Backend operational rules
├── frontend/
│   ├── index.html                      # Main HTML entry point
│   └── src/                            # React components, API client, styles
├── demo_nlp_extraction.py              # NLP extraction demo script
├── demo_itinerary_generation.py        # Itinerary generation demo script
├── CLAUDE.md                           # This file
├── todo.md                             # Task list & action items
└── PROJECT_STRUCTURE.md                # Full directory overview
```

**Import Convention**: All Python imports use short paths (e.g., `from config.settings import settings`), enabled by `sys.path.insert(0, os.path.dirname(__file__))` in `app.py`.

## Environment Configuration

### Required Environment Variables
```bash
# Gemini API Configuration (Primary LLM)
GEMINI_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash

# Groq API Configuration (Fallback LLM)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Flask Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=True

# NLP Extraction Settings
EXTRACTION_TEMPERATURE=0.2
EXTRACTION_MAX_TOKENS=2048

# Itinerary Generation Settings
ITINERARY_TEMPERATURE=0.7
ITINERARY_MAX_TOKENS=4096
```

### Setup Instructions
1. Copy `backend/.env.example` to `backend/.env`
2. Add your Gemini API key from https://aistudio.google.com/apikey
3. (Optional) Add your Groq API key from https://console.groq.com/keys for fallback
4. Activate virtual environment: `source venv/bin/activate` (Unix) or `venv\Scripts\activate` (Windows)
5. Install dependencies: `pip install -r backend/requirements.txt`
6. Run diagnostics: `python backend/diagnose.py`
7. Start server: `python backend/app.py`
8. Open browser: http://localhost:8000

## Known Issues & Solutions

### Issue: httpx version conflict with groq (fallback client)
**Symptom**: `Client.__init__() got an unexpected keyword argument 'proxies'`
**Solution**: Use `groq>=0.13.0` and `httpx>=0.27.0` in requirements.txt

### Issue: Gemini API key not configured
**Symptom**: `google.api_core.exceptions.PermissionDenied` or missing GEMINI_KEY
**Solution**: Ensure `GEMINI_KEY` is set in `.env` file. Get key from https://aistudio.google.com/apikey

### Issue: Empty model files
**Symptom**: `ImportError: cannot import name 'TripPreferences'`
**Solution**: Ensure all model files have proper content, not just empty files

## Pending Development (Phases 2-3)

### Phase 2: Itinerary Generation & MongoDB (IN PROGRESS)
- [x] Build Gemini prompt for itinerary creation (`services/itinerary_service.py`)
- [x] Implement feasibility validation (`itinerary_service._validate_feasibility()`)
- [x] Itinerary data model (`models/itinerary.py`)
- [ ] Add `/api/generate-itinerary` endpoint to `app.py`
- [ ] Set up MongoDB database and collections
- [ ] Implement venue data schema
- [ ] Seed database with 20-30 Kingston venues
- [ ] Add Google Maps API for geocoding
- [ ] Implement venue filtering by interests

### Phase 3: Advanced Features
- [ ] Add multi-modal transportation planning
- [ ] Integrate weather API
- [ ] Build real-time budget tracking
- [ ] Implement schedule adaptation engine
- [ ] Create Apache Airflow web scraping pipeline

## Testing Scenarios for Demo

### Test Case 1: Basic Extraction
**Input**: "I want to visit Kingston from March 15-17, 2026. Budget is $200. I'm interested in history and food."
**Expected**: Extract dates, budget ($67/day), interests [history, food], validate completeness

### Test Case 2: Budget Validation
**Input**: "Planning 3-day trip with $100 total budget"
**Expected**: Calculate $33/day, reject with message about $50/day minimum

### Test Case 3: Pace Preference
**Input**: "Want relaxed trip to Kingston, lots of time at museums"
**Expected**: Extract pace="relaxed", suggest 2-3 activities/day, 90-120 min per venue

### Test Case 4: Refinement
**Initial**: "Weekend trip to Kingston, love waterfront"
**Follow-up**: "Actually I'm vegetarian and need wheelchair access"
**Expected**: Update preferences while preserving previous inputs

## API Integration Details

### Gemini API (Primary)
- **SDK**: google-genai (`from google import genai`)
- **Model**: Configured via GEMINI_MODEL in settings.py
- **Temperature**: 0.2 (extraction) / 0.7 (itinerary generation)
- **Max Tokens**: 2048 (extraction) / 4096 (itinerary generation)
- **Configuration**: All Gemini settings in `config/settings.py` (no separate gemini.py)
- **API Key**: Set via `GEMINI_KEY` in .env

### Groq API (Fallback)
- **Model**: llama-3.3-70b-versatile
- **Temperature**: 0.2 (conservative, consistent extractions)
- **Max Tokens**: 2048
- **Response Format**: JSON mode enabled
- **Rate Limits**: Check Groq console for current limits

### Google Maps API (Planned)
- **Geocoding**: Validate starting locations
- **Distance Matrix**: Calculate travel times between venues
- **Directions**: Generate turn-by-turn routing
- **Places**: Search for nearby venues

### Weather API (Planned)
- **Forecast**: 7-day hourly forecasts
- **Historical**: Average weather for advance planning
- **Alerts**: Warning for outdoor activities

## MVP Success Criteria

The hackathon demo must show:
1. ✅ Natural language preference extraction (COMPLETE)
2. ✅ Validation and completeness scoring (COMPLETE)
3. ✅ Real-time UI updates (COMPLETE)
4. ✅ Itinerary generation service with Gemini API (IMPLEMENTED - needs API endpoint)
5. ⏳ MongoDB integration (PENDING)
6. ⏳ Multi-modal transportation planning (PENDING)
7. ⏳ Real-time weather tracking (PENDING)
8. ⏳ Real-time budget tracking (PENDING)
9. ⏳ Schedule adaptation (PENDING)
10. ⏳ Web scraping with change detection (PENDING)

## Team Work Distribution

**Developer 1**: UI & Data Collection (Phase 1 Complete)
- ✅ Conversational interface
- ✅ NLP extraction integration
- ⏳ Itinerary display UI

**Developer 2**: MongoDB & Core Logic
- ⏳ Database setup and schemas
- ⏳ Feasibility validation
- ⏳ Budget tracking
- ⏳ Adaptation engines

**Developer 3**: APIs & Web Scraping
- ⏳ Google Maps integration
- ⏳ Weather API
- ⏳ Transportation routing
- ⏳ Web scraping pipeline

## Conversation Flow (Phase 1)

### Information Collection Sequence
1. **Greeting** - Explain purpose, ask about visit type
2. **City & Country** - Destination (e.g., Kingston, Canada)
3. **Location Preference** - Area preference (downtown, waterfront, near nature)
4. **Dates & Duration** - Exact dates (YYYY-MM-DD) and duration
5. **Budget & Currency** - Total or daily (validate >= $50/day), currency
6. **Interests** - Select categories (min 1, optimal 2-4)
7. **Pace** - Relaxed, moderate, or packed schedule
8. **Optional Details** - Starting location, hours/day, transportation, group, dietary, accessibility, weather
9. **Confirmation** - Display summary, validate, proceed

### Handling Ambiguous Inputs
- **Vague location**: Ask for neighborhood or use downtown default
- **Unclear budget**: Provide ranges, enforce minimums
- **Generic interests**: Probe for specific categories
- **No pace specified**: Default to "moderate" with confirmation

## Prompt Engineering Patterns

### Extraction Prompt Structure
```python
"""Extract travel preferences from this user message:

User message: "{user_input}"

Return a JSON object with the following structure:
{json_schema}

Remember:
- Only include information that is mentioned or strongly implied
- Use null for missing information
- Return arrays as empty [] if no items are mentioned
- Return ONLY valid JSON, no additional text or explanation

JSON response:"""
```

### Refinement Prompt Structure
```python
"""You have previously extracted these preferences from a user:

{existing_preferences.to_json()}

The user has now provided additional information:
"{additional_input}"

Update the preferences JSON with the new information.
Keep existing values unless the new information contradicts or updates them.

Return the complete updated JSON object with the same structure:"""
```

## Important Notes for Claude

1. **Never remove fields** from TripPreferences without understanding full impact on NLP service, validation, and UI
2. **Always validate** user inputs against minimum requirements before proceeding
3. **Be conservative** in extraction - only extract explicitly mentioned information
4. **Maintain consistency** between extraction schema, validation rules, and UI display
5. **Follow the layered architecture** - don't mix concerns between routes, services, and clients
6. **Test thoroughly** after any changes to data models or extraction logic
7. **Document changes** to schemas, APIs, or core logic in this CLAUDE.md file

## Quick Reference Commands

```bash
# Activate environment
source venv/bin/activate  # Unix
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Run diagnostics
python backend/diagnose.py

# Test imports
python backend/test_imports.py

# Start server
python backend/app.py

# Run tests (when implemented)
pytest backend/tests/

# Format code
black backend/

# Lint code
flake8 backend/
```

## Resources & Documentation

- **Implementation Guide**: `Kingston-Trip-Planner_-MVP-Implementation-Guide-T.md`
- **Gemini API Docs**: https://ai.google.dev/gemini-api/docs
- **Groq API Docs**: https://console.groq.com/docs
- **Flask Documentation**: https://flask.palletsprojects.com/
- **MongoDB Python Driver**: https://pymongo.readthedocs.io/
- **Google Maps APIs**: https://developers.google.com/maps/documentation

---

**Last Updated**: 2026-02-07
**Phase**: Phase 1 Complete, Phase 2 (Itinerary Generation + MongoDB) In Progress
**Next Steps**: Add `/api/generate-itinerary` endpoint, MongoDB integration
