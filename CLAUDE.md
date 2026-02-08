# MonVoyage Trip Planner - Project Context for Claude

## Project Overview

MonVoyage is a real-time, AI-powered itinerary engine that generates feasible travel itineraries. The current MVP is a **conversational Toronto trip planner** with a chat-based UI. This is an MVP being built for a 2-week hackathon demonstration.

**Current Status**: Phase 2.5+ — Conversational Toronto MVP with Enriched Itineraries
**Team Size**: 3 developers
**Timeline**: 14 days
**Default City**: Toronto (hardcoded in chat flow; configurable via `DEFAULT_CITY` env var for legacy endpoints)

### Two Parallel Systems

1. **Conversational Chat** (primary, used by frontend): Single `/api/chat` endpoint with multi-turn conversation flow. Uses Groq (primary) / Gemini (fallback). Toronto-only. Produces grounded itineraries with `Source:` citations.
2. **Legacy Extraction** (still functional): `/api/extract` → `/api/refine` → `/api/generate-itinerary`. Uses Gemini (primary) / Groq (fallback). Supports any city.

## Project Goals

Build a working prototype that demonstrates:
1. AI-powered itinerary generation from natural language user input
2. Conversational multi-turn trip planning via chat interface
3. Grounded itineraries using only verified venue data (closed-world constraint)
4. Source citations on every activity for transparency and trust
5. Weather-aware activity recommendations
6. Automated venue data collection via Apache Airflow web scraping pipeline with change detection
7. Budget estimation with real Airbnb pricing and flight estimates

## Architecture Overview

### End-to-End Data Flow

#### Conversational Chat Flow (Primary — used by frontend)

```
Browser (index.html)
  |  POST /api/chat  {messages: [...], user_input: "..."}
  v
ConversationService.turn()
  |
  |  Phase 1: greeting  → hardcoded welcome (no LLM call)
  |  Phase 2: intake    → Groq/Gemini multi-turn chat
  |                        collects: dates, budget, interests, pace
  |                        appends "Still need: ..." to each response
  |  Phase 3: confirmed → user says "yes" to confirmation question
  |  Phase 4: itinerary → ItineraryOrchestrator.generate_enriched_itinerary()
  |            |
  |            |  State C: Extract TripPreferences from conversation (regex-based)
  |            |  State D: Parallel enrichment + LLM generation
  |            |    1. asyncio.gather: WeatherService + BudgetService + VenueService
  |            |    2. Build prompt (venues + weather context) → Groq/Gemini LLM
  |            |    3. GoogleMapsService.get_itinerary_routes() (post-LLM)
  |            |  State E: Assemble response (itinerary + weather + budget + routes)
  |            |
  |            |  Fail-soft: weather/budget/routes → null on failure
  |            |  Fatal: LLM failure → 500 error
  |            v
  |        Enriched itinerary (Day N + Source citations + weather + budget + routes)
  |
  +--- Airflow DB (PostgreSQL) <--- Airflow DAGs (daily scraping)
           |                             |
           |  places table               |  website_change_monitor DAG
           |  tracked_pages table        |  Fetches HTML -> extracts data
           |  page_snapshots table       |  Detects changes via content hash
           |  place_facts table          |  Updates Chroma vector index
           |  change_events table        |
           v                             v
       VenueService                  Chroma (vector search)
       (FastAPI reads)               (RAG retrieval)
```

#### Legacy Extraction Flow (still functional)

```
User Input (natural language)
  |
  v
NLPExtractionService (Gemini/Groq)       ← async, native await
  |  Extracts: city, dates, budget, interests, pace, etc.
  v
TripPreferences (validated)
  |
  +------> ItineraryService.generate_itinerary()    ← async
  |            |
  |            |  1. Validates preferences (10 required fields)
  |            |  2. Queries Airflow DB for real venues (VenueService)
  |            |  3. Builds Gemini prompt WITH venue data
  |            |  4. Calls Gemini API (async await)
  |            |  5. Parses response -> Itinerary dataclass
  |            |  6. Validates feasibility + database-only constraint
  |            v
  |        Itinerary (day-by-day timetable with from_database flags)
```

### Component Layers

**Backend** (FastAPI REST API):
- `app.py` - FastAPI application with lifespan management, CORS, 6 endpoints
- `schemas/` - Pydantic request/response models (API boundary validation)
- `services/` - Business logic:
  - `conversation_service.py` - Multi-turn chat lifecycle (greeting → intake → confirmed → itinerary)
  - `itinerary_orchestrator.py` - Orchestrates venue fetch, weather, budget, LLM itinerary, and routes ✅ NEW
  - `nlp_extraction_service.py` - NLP extraction from user input (async)
  - `itinerary_service.py` - Itinerary generation via Gemini + venue DB data (async)
  - `venue_service.py` - Reads venue data from Airflow PostgreSQL + Toronto fallback venues
  - `weather_service.py` - Weather forecasts via WeatherClient
  - `booking_service.py` - Accommodation + transportation booking orchestration
  - `trip_budget_service.py` - Trip cost estimation from preferences
  - `budget_estimator.py` - Core budget calculation (Airbnb scraping + flight estimates)
  - `google_maps_service.py` - Route planning and directions via Google Maps API
- `clients/` - External API wrappers:
  - `gemini_client.py` - Gemini API (async with retry, + sync `chat_with_history`)
  - `groq_client.py` - Groq API (sync: `generate_content`, `generate_json`, `chat_with_history`)
  - `weather_client.py` - Weather forecast API ✅ NEW
  - `airbnb_client.py` - Airbnb price scraping ✅ NEW
  - `flight_client.py` - Flight price estimation ✅ NEW
  - `busbud_client.py` - Bus/train booking links ✅ NEW
  - `google_maps_client.py` - Google Maps Directions API ✅ NEW
- `models/` - Data structures (TripPreferences, Itinerary)
- `config/` - Configuration management (settings.py)
- `utils/` - Helper functions

**Airflow Pipeline** (web scraping + RAG):
- `airflow/dags/website_monitor_dag.py` - Daily venue scraping DAG
- `airflow/dags/lib/db.py` - SQLAlchemy ORM models (Place, TrackedPage, etc.)
- `airflow/dags/lib/monitor.py` - HTML fetching + structured data extraction
- `airflow/dags/lib/chroma_index.py` - Chroma vector DB integration
- `airflow/dags/lib/retrieval.py` - RAG retrieval logic
- `airflow/dags/lib/seed_tracked_sites.py` - Database seeding (27 Toronto venues)

**Frontend**: Single-page HTML/CSS/JS chatbot interface
- Toronto Trip Planner branding
- Split-panel design: Chat interface | Phase-aware right panel
- Calls `/api/chat` endpoint exclusively (stateless server, client-side message history)
- Right panel shows: "What I know so far" during intake → enriched itinerary after generation
- Enrichment cards in right panel: Weather Forecast, Budget Estimate (with booking links), Day-by-Day Plan, Getting Around (route legs with Google Maps links)

**Database**: PostgreSQL (shared between Airflow and FastAPI)

## Technology Stack

### Core Technologies
- **Backend Framework**: FastAPI with uvicorn (migrated from Flask in Phase 2)
- **API Validation**: Pydantic v2 request/response schemas
- **AI/NLP**:
  - **Chat flow**: Groq API (primary, llama-3.3-70b-versatile) / Gemini API (fallback)
  - **Legacy extraction**: Gemini API (primary, gemini-3-flash-preview) / Groq API (fallback)
  - Both clients support `chat_with_history()` for multi-turn conversations
- **Language**: Python 3.8+
- **Database**: PostgreSQL (shared by Airflow and FastAPI via SQLAlchemy)
- **Vector DB**: Chroma (for RAG venue retrieval)
- **Orchestration**: Apache Airflow (web scraping + change detection)
- **APIs**: Google Maps API (implemented), Weather API (implemented), Airbnb scraping (implemented)

### Dependencies
```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
google-genai==1.62.0
groq>=0.13.0
httpx>=0.27.0
python-dotenv==1.0.0
python-dateutil==2.8.2
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio>=0.23.0
black==23.12.1
flake8==7.0.0
```

## Data Models

### TripPreferences Schema

#### Required Fields (10):
```python
@dataclass
class TripPreferences:
    # Location (any city, not limited to Kingston)
    city: str                           # REQUIRED - e.g., "Toronto", "Paris", "Tokyo"
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

#### Interest Categories (canonical names from NLP):
- **Food and Beverage** - restaurants, cafes, food tours, breweries, etc.
- **Entertainment** - shopping, casino, spa, nightlife, concerts, etc.
- **Culture and History** - museums, galleries, churches, monuments, etc.
- **Sport** - stadiums, golf, tennis, cycling, etc.
- **Natural Place** - parks, beaches, lakes, hiking, gardens, etc.

#### Optional Fields (with defaults):
```python
    starting_location: Optional[str] = None   # Default: "Downtown {city}"
    hours_per_day: int = 8
    transportation_modes: List[str] = None     # Default: ["mixed"]
    group_size: Optional[int] = None
    group_type: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = None
    accessibility_needs: Optional[List[str]] = None
    weather_tolerance: Optional[str] = None
    must_see_venues: Optional[List[str]] = None
    must_avoid_venues: Optional[List[str]] = None
```

### Activity Dataclass (includes `from_database` flag)
```python
@dataclass
class Activity:
    activity_id: str
    venue_name: str
    sequence: int
    planned_start: str          # HH:MM
    planned_end: str
    category: Optional[str]
    notes: Optional[str]
    duration_reason: Optional[str]
    estimated_cost: float
    from_database: bool = False  # True if sourced from Airflow venue DB
```

## Airflow Database Integration

### How It Works

1. **Airflow DAGs scrape venue websites** daily via `website_change_monitor` DAG
2. Scraped data is stored in PostgreSQL tables: `places`, `tracked_pages`, `page_snapshots`, `place_facts`, `change_events`
3. **VenueService** (FastAPI side) queries these same tables to get real venue data
4. **ItineraryService** calls `VenueService.get_venues_for_itinerary()` to fetch venues matching the user's city + interests
5. Venue data is injected into the Gemini prompt so the AI uses **real, verified venues**
6. Activities sourced from the DB are tagged with `from_database: true`

### Database Tables (defined in `airflow/dags/lib/db.py`)

| Table | Purpose |
|-------|---------|
| `places` | Master venue records (name, address, phone, hours, category, city) |
| `tracked_pages` | URLs to monitor per place (url, extract_strategy, css_rules) |
| `page_snapshots` | Historical snapshots with content hash for change detection |
| `place_facts` | Structured facts (hours, menu, price, tags) extracted per place |
| `change_events` | Change alerts when content hash differs between scrapes |

### Interest-to-DB Category Mapping

The NLP extractor outputs canonical interest names. `VenueService` maps them to DB categories:

```python
INTEREST_TO_DB_CATEGORIES = {
    "Food and Beverage": ["restaurant", "cafe", "bakery", "brewery", "food", "bar"],
    "Entertainment": ["entertainment", "shopping", "nightlife", "casino", "spa"],
    "Culture and History": ["museum", "gallery", "church", "historic", "tourism", "culture"],
    "Sport": ["sport", "stadium", "golf", "recreation"],
    "Natural Place": ["park", "garden", "nature", "beach", "trail", "island"],
}
```

### Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| PostgreSQL unreachable | `VenueService` uses `TORONTO_FALLBACK_VENUES` (15 built-in venues) for chat flow; returns empty list for legacy flow (Gemini uses its own knowledge) |
| `GROQ_API_KEY` not set | Chat endpoint falls back to Gemini; if Gemini also fails, returns 503 |
| `GEMINI_KEY` not set | Chat endpoint uses Groq only; legacy endpoints (`/api/extract`, `/api/refine`, `/api/generate-itinerary`) return 500 |
| Both LLM keys missing | Server refuses to start with configuration error |
| Groq API call fails | `ConversationService` falls back to Gemini mid-conversation |
| Google Maps API unavailable | `route_data` is `null` in response; itinerary still generated |
| Weather API unavailable | `weather_summary` is `null` in response; itinerary still generated (no weather context in prompt) |
| Budget estimation fails | `budget_summary` is `null` in response; itinerary still generated |
| All enrichment services fail | Core itinerary generated with venues only; all enrichment fields `null` |
| Orchestrator fails entirely | Falls back to legacy venue-only itinerary generation path |

## API Endpoints

Auto-generated API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Conversational Chat (Primary — used by frontend)
```
POST /api/chat
Request: {
  "messages": [                         // Full conversation history (client-side state)
    {"role": "system", "content": "..."},
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "user_input": "I want to visit March 15-17..."   // Latest user message (null for greeting)
}
Response: {
  "success": boolean,
  "messages": ChatMessage[],            // Updated conversation history (send back next turn)
  "assistant_message": string,          // Latest assistant response
  "phase": string,                      // "greeting" | "intake" | "confirmed" | "itinerary"
  "still_need": string[] | null,        // e.g., ["budget", "interests"] or null
  "error": string | null,
  // ── Enrichment fields (populated only in itinerary phase) ──
  "weather_summary": string | null,     // Human-readable weather for trip dates
  "budget_summary": {                   // null if budget estimation unavailable
    "within_budget": boolean,
    "cheapest_total": float | null,
    "average_total": float | null,
    "remaining_budget": float | null,
    "links": { "airbnb": string | null, ... } | null
  } | null,
  "route_data": [                       // null if Google Maps unavailable
    { "leg": int, "origin": string, "destination": string,
      "duration": string | null, "distance": string | null,
      "mode": string | null, "google_maps_link": string | null }
  ] | null
}
```

### Health Check
```
GET /api/health
Response: {
  "status": "healthy",
  "service": "MonVoyage Trip Planner",
  "primary_llm": "gemini" | "groq",
  "model": string,
  "nlp_service_ready": boolean,
  "error": string | null
}
```

### Extract Preferences (Legacy)
```
POST /api/extract
Request: {
  "user_input": "I want to visit Toronto next weekend with my family..."
}
Response: {
  "success": boolean,
  "preferences": TripPreferences,
  "validation": {
    "valid": boolean,
    "issues": string[],
    "warnings": string[],
    "completeness_score": float (0.0-1.0)
  },
  "bot_message": string,
  "saved_to_file": string | null
}
```

### Refine Preferences (Legacy)
```
POST /api/refine
Request: {
  "preferences": {...},
  "additional_input": "I'm vegetarian and want to see the CN Tower"
}
Response: {
  "success": boolean,
  "preferences": TripPreferences,
  "validation": {...},
  "bot_message": string,
  "saved_to_file": string | null
}
```

### Generate Itinerary (Legacy)
```
POST /api/generate-itinerary
Request: {
  "preferences": {...}  # Complete TripPreferences dict (all 10 required fields)
}
Response: {
  "success": boolean,
  "itinerary": Itinerary,  # Day-by-day timetable
  "feasibility": {
    "feasible": boolean,
    "issues": string[],
    "warnings": string[]
  }
}
```

## Conversational Chat Flow (Toronto MVP)

### Overview

The `/api/chat` endpoint powers a stateless, multi-turn conversation for planning Toronto trips. The server holds no session state — the full message history is stored client-side and sent with every request.

### Phases

```
greeting  →  intake  →  confirmed  →  itinerary
```

| Phase | Trigger | LLM Call | Output |
|-------|---------|----------|--------|
| `greeting` | Empty `messages` array | None (hardcoded) | Welcome message + `Still need: travel dates, budget, interests, pace` |
| `intake` | User provides trip details | Groq/Gemini with `INTAKE_SYSTEM_PROMPT` | Acknowledge + ask for missing info + `Still need: ...` |
| `confirmed` | All 4 fields collected | Groq/Gemini detects completion | "Want me to generate your Toronto itinerary now?" |
| `itinerary` | User confirms ("yes", "sure", etc.) | Groq/Gemini with `ITINERARY_SYSTEM_PROMPT` | Day-by-day plan with Source citations |

### Required Intake Fields (4)

| Field | Example |
|-------|---------|
| Travel dates | March 15-17, 2026 |
| Budget | $300 CAD total |
| Interests | Museums, food, parks |
| Pace | Relaxed / Moderate / Packed |

### Confirmation Detection

The system detects confirmation via two conditions (both must be true):
1. The previous assistant message contains the marker: `"generate your Toronto itinerary"`
2. The user's input matches an affirmative pattern: `yes`, `yeah`, `sure`, `go ahead`, `let's do it`, `absolutely`, `ok`, `sounds good`, `yes please`, etc.

If only condition 2 is true (user says "yes" but no confirmation was asked), the conversation stays in intake phase.

### Grounded Itinerary Generation

When confirmed, `ConversationService` generates the itinerary:

1. Fetches Toronto venues via `VenueService.get_toronto_venues()` (DB or fallback)
2. Formats venues via `VenueService.format_venues_for_chat()`:
   ```
   [venue_id: cn_tower] CN Tower [tourism] — 290 Bremner Blvd, Toronto | URL: https://www.cntower.ca
   ```
3. Builds the itinerary system prompt with the venue catalogue injected
4. Calls Groq (primary) or Gemini (fallback) with the full conversation context
5. Returns a day-by-day plan in this exact format:

```
Day 1
Morning: Visit the Royal Ontario Museum — Royal Ontario Museum (Source: rom, https://www.rom.on.ca)
Afternoon: Lunch at St. Lawrence Market — St. Lawrence Market (Source: st_lawrence_market, https://www.stlawrencemarket.com)
Evening: Explore the Distillery District — Distillery Historic District (Source: distillery_district, https://www.thedistillerydistrict.com)
```

### QA Constraints

- **Still need**: Every intake response ends with `Still need: <comma-separated list>`
- **100% Source coverage**: Every Morning/Afternoon/Evening line must have `Source: {venue_id}, {url}`
- **Closed-world**: ONLY venues from the venue list may be used; invented venues are rejected
- **Negative rejection**: If user asks for a venue not in the list, the assistant refuses and offers alternatives

### LLM Fallback in Chat

`ConversationService.__init__()` tries Groq first. If unavailable, falls back to Gemini. If a Groq call fails mid-conversation, the service dynamically falls back to Gemini for that call.

## Itinerary Generation Flow (Legacy)

### Step-by-Step Process

1. **Validate preferences** — 10 required fields checked, budget >= $50/day
2. **Fetch venues from Airflow DB** — `VenueService.get_venues_for_itinerary(city, interests, budget)` (async via run_in_executor)
3. **Build Gemini prompt** — includes trip details + available venues from DB
4. **Call Gemini API** — async await, with system instruction for itinerary generation
5. **Parse JSON response** — extract itinerary structure
6. **Build Itinerary object** — map JSON to dataclass hierarchy
7. **Validate feasibility** — day count, meals, budget, activity count, interest coverage

### Gemini System Instruction (Legacy Flow Key Points)
- Generates itineraries for **any city** (not hardcoded to Kingston)
- When venue data from DB is provided, **prefers those venues** over invented ones
- Activities from the DB are marked with `from_database: true`
- Follows pace-specific parameters (relaxed/moderate/packed)
- Returns structured JSON matching the schema

### Pace-Specific Parameters
| Pace | Activities/day | Duration | Buffer | Lunch | Dinner |
|------|---------------|----------|--------|-------|--------|
| Relaxed | 2-3 | 90-120 min | 20 min | 90 min | 120 min |
| Moderate | 4-5 | 60-90 min | 15 min | 60 min | 90 min |
| Packed | 6-8 | 30-60 min | 5 min | 45 min | 60 min |

## Current File Structure

```
MonVoyage/
├── backend/
│   ├── app.py                          # FastAPI application (6 endpoints, lifespan mgmt)
│   ├── config/
│   │   └── settings.py                 # Configuration (Gemini + Groq + DB URL + pace params)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── api_models.py              # Pydantic: ExtractReq, RefineReq, ChatReq/Resp, etc.
│   ├── models/
│   │   ├── trip_preferences.py         # TripPreferences dataclass (pace synonyms, interest mapping)
│   │   └── itinerary.py               # Itinerary, Activity (from_database), Meal, TravelSegment
│   ├── services/
│   │   ├── conversation_service.py     # Multi-turn chat: greeting→intake→confirmed→itinerary
│   │   ├── itinerary_orchestrator.py   # Orchestrates enrichment: weather+budget+venues+LLM+routes ✅ NEW
│   │   ├── nlp_extraction_service.py   # NLP extraction from user input (async)
│   │   ├── itinerary_service.py        # Itinerary generation + venue DB integration (async)
│   │   ├── venue_service.py            # Airflow DB queries + TORONTO_FALLBACK_VENUES (15)
│   │   ├── weather_service.py          # Weather forecasts for trip dates
│   │   ├── booking_service.py          # Airbnb + flights + bus booking orchestration
│   │   ├── trip_budget_service.py      # Trip cost estimation wrapper
│   │   ├── budget_estimator.py         # Core budget calc (Airbnb scraping + flight estimates)
│   │   └── google_maps_service.py      # Route planning + directions via Google Maps
│   ├── clients/
│   │   ├── gemini_client.py            # Gemini API (async generate_content + sync chat_with_history)
│   │   ├── groq_client.py             # Groq API (generate_content, generate_json, chat_with_history)
│   │   ├── weather_client.py           # Weather forecast API wrapper ✅ NEW
│   │   ├── airbnb_client.py            # Airbnb price scraping ✅ NEW
│   │   ├── flight_client.py            # Flight price estimation ✅ NEW
│   │   ├── busbud_client.py            # Bus/train booking links ✅ NEW
│   │   └── google_maps_client.py       # Google Maps Directions API ✅ NEW
│   ├── routes/
│   │   └── trip_routes.py              # Route definitions (stub - TODO)
│   ├── controllers/
│   │   └── trip_controller.py          # Business logic handlers (stub - TODO)
│   ├── storage/
│   │   ├── trip_json_repo.py           # Trip persistence (stub - TODO)
│   │   └── itinerary_json_repo.py      # Itinerary persistence (stub - TODO)
│   ├── utils/
│   │   └── id_generator.py             # Trip/itinerary ID generation
│   ├── data/
│   │   └── trip_requests/              # Saved trip preference JSON files
│   ├── .env.example
│   ├── diagnose.py
│   └── test_imports.py
├── airflow/
│   └── dags/
│       ├── website_monitor_dag.py      # Daily web scraping DAG
│       ├── trip_placeholder_dag.py     # Deprecated placeholder
│       └── lib/
│           ├── db.py                   # SQLAlchemy ORM: Place, TrackedPage, etc.
│           ├── monitor.py             # HTML fetch + structured extraction
│           ├── chroma_index.py        # Chroma vector DB integration
│           ├── retrieval.py           # RAG retrieval logic
│           ├── seed_tracked_sites.py  # Database seeding (27 Toronto venues)
│           └── __init__.py
├── frontend/
│   ├── index.html                      # Toronto Trip Planner chat UI (calls /api/chat)
│   └── src/                            # React components, API client, styles
├── doc/
│   ├── WORKFLOW_GUIDE.md               # Conversational MVP usage + testing guide ✅ NEW
│   └── ...                             # Other documentation files
├── test/
│   ├── test_orchestrator.py            # 23 unit tests for ItineraryOrchestrator ✅ NEW
│   ├── validate_workflow.py            # Automated workflow validation vs running server ✅ NEW
│   ├── demo_nlp_extraction.py
│   ├── demo_itinerary_generation.py
│   └── test_extraction.py
├── requirements.txt                    # Project dependencies (FastAPI, uvicorn, etc.)
├── CLAUDE.md                           # This file
└── PROJECT_STRUCTURE.md
```

**Import Convention**: All Python imports use short paths (e.g., `from config.settings import settings`), enabled by `sys.path.insert(0, os.path.dirname(__file__))` in `app.py`.

## Environment Configuration

### Required Environment Variables
```bash
# Gemini API Configuration (Primary for legacy extraction; fallback for chat)
GEMINI_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3-flash-preview

# Groq API Configuration (Primary for chat; fallback for legacy extraction)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# FastAPI Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=True

# Airflow / Venue Database (PostgreSQL shared with Airflow)
APP_DB_URL=postgresql+psycopg2://app:app@localhost:5432/app

# Default City (multi-city support — change to target any city)
DEFAULT_CITY=Toronto
DEFAULT_COUNTRY=Canada

# NLP Extraction Settings
EXTRACTION_TEMPERATURE=0.2
EXTRACTION_MAX_TOKENS=2048

# Itinerary Generation Settings
ITINERARY_TEMPERATURE=0.7
ITINERARY_MAX_TOKENS=8192

# Google Maps API (Optional — for route enrichment)
GOOGLE_MAPS_API_KEY=
```

### Setup Instructions
1. Copy `backend/.env.example` to `backend/.env`
2. Add at least one LLM API key:
   - **For chat flow**: `GROQ_API_KEY` from https://console.groq.com/keys (recommended)
   - **For legacy extraction**: `GEMINI_KEY` from https://aistudio.google.com/apikey
   - **Both**: Chat uses Groq primary + Gemini fallback; legacy uses Gemini primary + Groq fallback
3. (Optional) Set `APP_DB_URL` to your PostgreSQL connection string (same DB as Airflow)
4. (Optional) Set `GOOGLE_MAPS_API_KEY` for route enrichment (without it, `route_data` will be `null`)
5. Activate virtual environment: `source venv/bin/activate`
6. Install dependencies: `pip install -r requirements.txt`
7. Run diagnostics: `python backend/diagnose.py`
8. Start server: `python backend/app.py`
9. Open browser: http://localhost:8000
10. View API docs: http://localhost:8000/docs

### Airflow Setup
1. Start PostgreSQL (via Docker or local install)
2. Seed the database: `python airflow/dags/lib/seed_tracked_sites.py`
3. Start Airflow: `airflow standalone` or via Docker Compose
4. Enable the `website_change_monitor` DAG in the Airflow UI
5. The DAG runs daily and populates the `places` table with scraped venue data

## Airflow Guide: How the Database Works

### Airflow DAG → PostgreSQL → FastAPI (read path)

```
Airflow (write)                PostgreSQL                  FastAPI (read)
+-----------------------+      +-------------------+      +-------------------+
| website_change_monitor|      |                   |      |                   |
|   list_sites()        | ---> | places            | <--- | VenueService      |
|   check_one_site()    |      | tracked_pages     |      |   get_venues_..() |
|   fetch_html()        |      | page_snapshots    |      |                   |
|   extract_structured()|      | place_facts       |      | ItineraryService  |
|   upsert_place_and_   |      | change_events     |      |   _fetch_venues() |
|     snapshot()         |      |                   |      |   _build_prompt() |
|   update chroma index |      +-------------------+      +-------------------+
+-----------------------+
```

### Key Database Operations

**Airflow writes** (in `monitor.py`):
- `upsert_place_and_snapshot()` — creates/updates a `Place` row + inserts a `PageSnapshot`
- Change detection via SHA-256 content hash comparison
- If content changed, a `ChangeEvent` is recorded

**FastAPI reads** (in `venue_service.py`):
- `get_venues_for_itinerary(city, interests, budget)` — queries `places` table
- Filters by city (ILIKE) and category (mapped from interests)
- Returns venue dicts injected into the Gemini prompt

### Seeding Venues for a New City

To add venues for a new city (e.g., Toronto):

1. Add place entries to `seed_tracked_sites.py`:
```python
PLACES = [
    {
        "place_key": "cn_tower",
        "canonical_name": "CN Tower",
        "city": "Toronto",
        "category": "tourism",
    },
    {
        "place_key": "st_lawrence_market",
        "canonical_name": "St. Lawrence Market",
        "city": "Toronto",
        "category": "food",
    },
]
```

2. Add tracked pages with URLs to scrape:
```python
PAGES = [
    {
        "place_key": "cn_tower",
        "url": "https://www.cntower.ca/",
        "page_type": "overview",
        "extract_strategy": "jsonld",
    },
]
```

3. Run the seeder: `python airflow/dags/lib/seed_tracked_sites.py`
4. Trigger the DAG to scrape: `airflow dags trigger website_change_monitor`

### Airflow Connections & Variables

**Connection** (for PostgresHook in DAGs):
```bash
export AIRFLOW_CONN_APP_POSTGRES='postgresql://app:app@localhost:5432/app'
```

**Variables** (optional, for scraping config):
```bash
airflow variables set scrape_config '{"max_retries": 3, "delay_seconds": 2}' --json
```

## Toronto Fallback Venues

When PostgreSQL is unreachable, `VenueService.get_toronto_venues()` returns 15 built-in fallback venues:

| venue_id | Name | Category |
|----------|------|----------|
| `cn_tower` | CN Tower | tourism |
| `rom` | Royal Ontario Museum | museum |
| `st_lawrence_market` | St. Lawrence Market | food |
| `ripley_aquarium` | Ripley's Aquarium of Canada | entertainment |
| `high_park` | High Park | park |
| `distillery_district` | Distillery Historic District | culture |
| `kensington_market` | Kensington Market | food |
| `hockey_hall_of_fame` | Hockey Hall of Fame | sport |
| `casa_loma` | Casa Loma | culture |
| `ago` | Art Gallery of Ontario | museum |
| `toronto_islands` | Toronto Islands | park |
| `harbourfront_centre` | Harbourfront Centre | entertainment |
| `bata_shoe_museum` | Bata Shoe Museum | museum |
| `toronto_zoo` | Toronto Zoo | entertainment |
| `aga_khan_museum` | Aga Khan Museum | museum |

The full seed database (`seed_tracked_sites.py`) contains 27 Toronto venues including additional entries like Steam Whistle Brewery, Rogers Centre, Scotiabank Arena, Toronto Eaton Centre, and others.

## Enrichment Services (Wired via ItineraryOrchestrator)

The following services are wired into the chat flow via `ItineraryOrchestrator`. They run in parallel during the itinerary phase and all degrade gracefully to `null` on failure:

### WeatherService (`weather_service.py`)
- Fetches weather forecasts for trip dates via `WeatherClient` (Open-Meteo API, no key needed)
- Returns daily forecasts: condition, temp_min/max, precipitation, wind speed, sunrise/sunset
- **Wired**: Weather context injected into LLM prompt; summary returned as `weather_summary` in response
- Key method: `get_trip_weather(preferences)` → Dict with forecasts per day

### TripBudgetService (`trip_budget_service.py`) + BudgetEstimator (`budget_estimator.py`)
- Estimates total trip costs using real Airbnb prices + flight price estimates
- Returns 3 scenarios: cheapest, average, most expensive
- Includes booking links (Skyscanner, Airbnb, BusBud)
- **Wired**: Budget estimation returned as `budget_summary` in response with booking links
- Key method: `estimate_trip_budget(preferences)` → Dict with cost breakdown

### GoogleMapsService (`google_maps_service.py`)
- Route planning between venues using Google Maps Directions API
- Supports driving, transit, and walking modes
- Falls back to Google Maps URL generation when API unavailable
- **Wired**: Routes fetched post-LLM from venue names in itinerary; returned as `route_data`
- Key method: `get_itinerary_routes(venue_names, city, country, mode)` → List[Dict]
- Requires `GOOGLE_MAPS_API_KEY` in `.env` (optional — `route_data` is `null` without it)

### BookingService (`booking_service.py`)
- Orchestrates accommodation + transportation booking
- Uses `AirbnbClient` (price scraping), `FlightClient` (estimates), `BusbudClient` (links)
- Supports 4 booking types: `"none"`, `"accommodation"`, `"transportation"`, `"both"`
- **Not yet wired** to chat flow (used indirectly via TripBudgetService for cost estimation)
- Key method: `book_trip(preferences)` → Dict with links and results

### ItineraryOrchestrator (`itinerary_orchestrator.py`)

The orchestrator is the central coordinator for the enriched itinerary workflow:

1. **Preference extraction** (State C): Regex-based extraction of dates, budget, interests, pace from conversation history — avoids extra LLM call
2. **Parallel enrichment** (State D): `asyncio.gather` fetches weather + budget + venues simultaneously
3. **LLM generation** (State D): Builds prompt with venue catalogue + weather context → Groq/Gemini
4. **Route enrichment** (State D): Extracts venue names from itinerary text → GoogleMaps route fetch
5. **Response assembly** (State E): Combines itinerary text + weather summary + budget summary + route data

**Error handling**: All enrichment failures are logged at WARNING and return `null`. Only LLM failure is fatal (raises exception → 500). The orchestrator itself is optional — if it fails entirely, `ConversationService` falls back to the legacy venue-only generation path.

## Validation Rules

- **Budget**: Daily budget MUST BE >= $50 (for two meals + activities)
- **Dates**: Start date must be today or future, end date must be after start
- **Interests**: At least 1 required, optimal 2-4, max 6
- **Pace**: Must be one of "relaxed", "moderate", or "packed"

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

## Testing Scenarios for Demo

### Conversational Chat Flow Tests

#### Test Case 1: Full Conversation Flow
1. Open http://localhost:8000 — greeting appears automatically
2. Type: "I want to visit March 15-17, budget $300, love museums and food, moderate pace"
3. Assistant should recognize all 4 fields → ask confirmation
4. Type: "Yes" → generates grounded itinerary with Source citations
**Verify**: Every activity has `Source: {venue_id}, {url}`

#### Test Case 2: Multi-Turn Intake
1. Type: "March 15-17" → assistant asks for budget
2. Type: "$300" → assistant asks for interests
3. Type: "museums and food" → assistant asks for pace
4. Type: "moderate" → confirmation question
**Verify**: `Still need:` list shrinks after each turn

#### Test Case 3: Closed-World Enforcement
1. Complete intake, get confirmation
2. During intake, say: "I want to visit the Eiffel Tower"
3. **Expected**: Assistant refuses and suggests alternatives from the Toronto venue list

#### Test Case 4: Graceful Degradation (No DB)
- Stop PostgreSQL, restart server
- **Expected**: Chat flow works using `TORONTO_FALLBACK_VENUES`; itinerary still has Source citations

### Legacy Endpoint Tests

#### Test Case 5: Basic Extraction (Multi-City)
**Input**: `POST /api/extract` with "I want to visit Toronto from March 15-17, 2026. Budget is $300."
**Expected**: Extract city=Toronto, dates, budget ($100/day), interests

#### Test Case 6: Budget Validation
**Input**: `POST /api/extract` with "Planning 3-day trip with $100 total budget"
**Expected**: Calculate $33/day, reject with message about $50/day minimum

## Known Issues & Solutions

### Issue: httpx version conflict with groq (fallback client)
**Symptom**: `Client.__init__() got an unexpected keyword argument 'proxies'`
**Solution**: Use `groq>=0.13.0` and `httpx>=0.27.0` in requirements.txt

### Issue: Gemini API key not configured
**Symptom**: `google.api_core.exceptions.PermissionDenied` or missing GEMINI_KEY
**Solution**: Ensure `GEMINI_KEY` is set in `.env` file

### Issue: PostgreSQL connection refused
**Symptom**: `psycopg2.OperationalError: connection refused`
**Solution**: Ensure PostgreSQL is running and `APP_DB_URL` is correct in `.env`

### Issue: No venues returned from DB
**Symptom**: Itinerary generated without `from_database` flags
**Solution**: Seed the database for the target city and run the Airflow DAG

## Important Notes for Claude

1. **Two parallel systems**: Chat flow (`/api/chat`) is Toronto-only; legacy flow supports any city
2. **Never remove fields** from TripPreferences without understanding full impact
3. **Always validate** user inputs against minimum requirements before proceeding
4. **Be conservative** in extraction — only extract explicitly mentioned information
5. **Follow the layered architecture** — don't mix concerns between schemas, services, and clients
6. **Venue DB is optional** — the system must work even if PostgreSQL is unreachable (fallback venues exist)
7. **Document changes** to schemas, APIs, or core logic in this CLAUDE.md file
8. **FastAPI async pattern** — service methods are async; sync I/O (Groq, SQLAlchemy) uses `run_in_executor`
9. **Closed-world constraint** — itineraries from `/api/chat` must ONLY use venues from the venue list
10. **Source citations** — every itinerary activity must include `Source: {venue_id}, {url}`
11. **Dual-LLM** — ConversationService tries Groq first, falls back to Gemini; legacy services do the reverse
12. **Enrichment is fail-soft** — weather/budget/routes return `null` on failure; only LLM failure is fatal
13. **Orchestrator is optional** — if `ItineraryOrchestrator` fails, `ConversationService` falls back to legacy venue-only path
14. **No internal system names in user messages** — enrichment failures should never be mentioned to the user; data is in structured response fields only

## Pending Development

### Phase 2 (COMPLETE)
- [x] Build Gemini prompt for itinerary creation
- [x] Implement feasibility validation
- [x] Itinerary data model with `from_database` flag
- [x] VenueService to query Airflow DB from FastAPI
- [x] Integrate venue data into itinerary generation prompt
- [x] Multi-city support (removed Kingston-only hardcoding)
- [x] Add `/api/generate-itinerary` endpoint to `app.py`
- [x] Migrate Flask → FastAPI with async/await, Pydantic validation, auto-docs

### Phase 2.5 — Conversational Toronto MVP (COMPLETE)
- [x] Seed database with 27 Toronto venues
- [x] Add `chat_with_history()` to GroqClient and GeminiClient
- [x] Create `ConversationService` with 4-phase flow (greeting → intake → confirmed → itinerary)
- [x] Add `/api/chat` endpoint with ChatRequest/ChatResponse schemas
- [x] Implement closed-world itinerary generation with Source citations
- [x] Add `TORONTO_FALLBACK_VENUES` (15 venues) for DB-free demo
- [x] Rewrite frontend for Toronto Trip Planner with `/api/chat` integration
- [x] Create `doc/WORKFLOW_GUIDE.md`
- [x] Implement WeatherService + WeatherClient
- [x] Implement BookingService (Airbnb + flights + buses)
- [x] Implement TripBudgetService + BudgetEstimator
- [x] Implement GoogleMapsService + GoogleMapsClient
- [x] Dual-LLM support (Groq primary → Gemini fallback) in ConversationService

### Phase 2.5+ — Enriched Itinerary Workflow (COMPLETE)
- [x] Create `ItineraryOrchestrator` to coordinate all enrichment services
- [x] Wire WeatherService into chat flow (weather context in LLM prompt + `weather_summary` response)
- [x] Wire TripBudgetService into chat flow (`budget_summary` response with booking links)
- [x] Wire GoogleMapsService into chat flow (`route_data` response with directions)
- [x] Regex-based preference extraction from conversation history (no extra LLM call)
- [x] Parallel service execution with `asyncio.gather` + fail-soft error handling
- [x] Extend `ChatResponse` schema with `weather_summary`, `budget_summary`, `route_data`
- [x] Update frontend right panel with enrichment cards (weather, budget, routes)
- [x] Create `test/test_orchestrator.py` with 23 unit tests
- [x] Create `test/validate_workflow.py` automated validation script
- [x] Backwards-compatible: orchestrator failure falls back to legacy venue-only path

### Phase 3: Advanced Features
- [ ] Wire BookingService directly to API endpoints (accommodation + transport booking)
- [ ] Multi-modal transportation planning with real Google Maps routes in itinerary
- [ ] Schedule adaptation engine (re-generate itinerary with updated preferences)
- [ ] Expand Airflow scraping to more cities beyond Toronto
- [ ] Add Google Maps geocoding for venue location validation
- [ ] User authentication + trip persistence (save/load itineraries)
- [ ] Multi-language support

## Quick Reference Commands

```bash
# Activate environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server (uvicorn with hot reload)
python backend/app.py

# Or run directly with uvicorn (from backend/ directory)
cd backend && uvicorn app:app --reload

# View API docs
open http://localhost:8000/docs

# Seed venue database
python airflow/dags/lib/seed_tracked_sites.py

# Start Airflow (standalone dev mode)
airflow standalone

# Trigger scraping DAG manually
airflow dags trigger website_change_monitor

# Run all tests
pytest test/

# Run orchestrator unit tests (23 tests)
pytest test/test_orchestrator.py -v

# Run automated workflow validation (requires running server)
python3 test/validate_workflow.py

# Format code
black backend/

# Lint code
flake8 backend/
```

## Resources & Documentation

- **Gemini API Docs**: https://ai.google.dev/gemini-api/docs
- **Groq API Docs**: https://console.groq.com/docs
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Pydantic v2 Docs**: https://docs.pydantic.dev/latest/
- **Apache Airflow Docs**: https://airflow.apache.org/docs/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **Chroma Docs**: https://docs.trychroma.com/
- **Google Maps APIs**: https://developers.google.com/maps/documentation

---

**Last Updated**: 2026-02-08
**Phase**: Phase 2.5+ Complete (Enriched Itinerary Workflow with Weather/Budget/Routes)
**Next Steps**: Wire BookingService to API endpoints, schedule adaptation engine, multi-city expansion
