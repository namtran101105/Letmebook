# MonVoyage Trip Planner - Project Context for Claude

## Project Overview

MonVoyage is a real-time, AI-powered itinerary engine that generates feasible travel itineraries for **any city** (currently defaulting to Toronto, Canada). This is an MVP being built for a 2-week hackathon demonstration.

**Current Status**: Phase 2 Complete (FastAPI migration + Itinerary Generation + Airflow DB Integration)
**Team Size**: 3 developers
**Timeline**: 14 days
**Default City**: Toronto (configurable via `DEFAULT_CITY` env var)

## Project Goals

Build a working prototype that demonstrates:
1. AI-powered itinerary generation from natural language user input
2. Real-time travel planning with multi-modal transportation
3. Dynamic budget tracking and schedule adaptation
4. Weather-aware activity recommendations
5. Automated venue data collection via Apache Airflow web scraping pipeline with change detection
6. Multi-city support (any city, not limited to a single destination)

## Architecture Overview

### End-to-End Data Flow

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
  |            |  1. Validates preferences
  |            |  2. Queries Airflow DB for real venues (VenueService)  ← async via run_in_executor
  |            |  3. Builds Gemini prompt WITH venue data
  |            |  4. Calls Gemini API (async await)
  |            |  5. Parses response -> Itinerary dataclass
  |            |  6. Validates feasibility
  |            v
  |        Itinerary (day-by-day timetable)
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

### Component Layers

**Backend** (FastAPI REST API):
- `app.py` - FastAPI application with lifespan management, CORS, 5 endpoints
- `schemas/` - Pydantic request/response models (API boundary validation)
- `services/` - Business logic:
  - `nlp_extraction_service.py` - NLP extraction from user input (async)
  - `itinerary_service.py` - Itinerary generation via Gemini + venue DB data (async)
  - `venue_service.py` - Reads venue data from Airflow-managed PostgreSQL
- `clients/` - External API wrappers (Gemini, Groq)
- `models/` - Data structures (TripPreferences, Itinerary)
- `config/` - Configuration management (settings.py)
- `utils/` - Helper functions

**Airflow Pipeline** (web scraping + RAG):
- `airflow/dags/website_monitor_dag.py` - Daily venue scraping DAG
- `airflow/dags/lib/db.py` - SQLAlchemy ORM models (Place, TrackedPage, etc.)
- `airflow/dags/lib/monitor.py` - HTML fetching + structured data extraction
- `airflow/dags/lib/chroma_index.py` - Chroma vector DB integration
- `airflow/dags/lib/retrieval.py` - RAG retrieval logic
- `airflow/dags/lib/seed_tracked_sites.py` - Database seeding

**Frontend**: Single-page HTML/CSS/JS chatbot interface
- Split-panel design: Chat interface | Extracted preferences display
- Real-time preference extraction and validation

**Database**: PostgreSQL (shared between Airflow and FastAPI)

## Technology Stack

### Core Technologies
- **Backend Framework**: FastAPI with uvicorn (migrated from Flask in Phase 2)
- **API Validation**: Pydantic v2 request/response schemas
- **AI/NLP**: Gemini API (primary, via google-genai SDK) / Groq API (fallback, llama-3.3-70b-versatile model)
- **Language**: Python 3.8+
- **Database**: PostgreSQL (shared by Airflow and FastAPI via SQLAlchemy)
- **Vector DB**: Chroma (for RAG venue retrieval)
- **Orchestration**: Apache Airflow (web scraping + change detection)
- **APIs**: Google Maps API (planned), Weather API (planned)

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

If the Airflow DB is unreachable, `ItineraryService` still works — it generates the itinerary without real venue data (Gemini uses its own knowledge). The `_fetch_venues()` method catches exceptions and returns an empty list.

## API Endpoints

Auto-generated API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Health Check
```
GET /api/health
Response: {
  "status": "healthy",
  "service": "MonVoyage Trip Planner",
  "primary_llm": "gemini",
  "model": "Gemini (gemini-3-flash-preview)",
  "nlp_service_ready": boolean,
  "error": string | null
}
```

### Extract Preferences (Initial)
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

### Refine Preferences (Follow-up)
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

### Generate Itinerary
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

## Itinerary Generation Flow

### Step-by-Step Process

1. **Validate preferences** — 10 required fields checked, budget >= $50/day
2. **Fetch venues from Airflow DB** — `VenueService.get_venues_for_itinerary(city, interests, budget)` (async via run_in_executor)
3. **Build Gemini prompt** — includes trip details + available venues from DB
4. **Call Gemini API** — async await, with system instruction for itinerary generation
5. **Parse JSON response** — extract itinerary structure
6. **Build Itinerary object** — map JSON to dataclass hierarchy
7. **Validate feasibility** — day count, meals, budget, activity count, interest coverage

### Gemini System Instruction (Key Points)
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
│   ├── app.py                          # FastAPI application entry point (uvicorn, port 8000)
│   ├── config/
│   │   └── settings.py                 # Configuration (Gemini + Groq + DB URL)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── api_models.py              # Pydantic request/response models ✅ NEW
│   ├── models/
│   │   ├── trip_preferences.py         # TripPreferences dataclass
│   │   └── itinerary.py               # Itinerary data structures (with from_database flag)
│   ├── services/
│   │   ├── nlp_extraction_service.py   # NLP extraction logic (async) ✅
│   │   ├── itinerary_service.py        # Itinerary generation + venue DB integration (async) ✅
│   │   └── venue_service.py            # Reads venue data from Airflow PostgreSQL ✅
│   ├── clients/
│   │   ├── gemini_client.py            # Gemini API wrapper (primary, async) ✅
│   │   └── groq_client.py             # Groq API wrapper (fallback, sync) ✅
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
│       ├── website_monitor_dag.py      # Daily web scraping DAG ✅
│       ├── trip_placeholder_dag.py     # Deprecated placeholder
│       └── lib/
│           ├── db.py                   # SQLAlchemy ORM: Place, TrackedPage, etc. ✅
│           ├── monitor.py             # HTML fetch + structured extraction ✅
│           ├── chroma_index.py        # Chroma vector DB integration ✅
│           ├── retrieval.py           # RAG retrieval logic ✅
│           ├── seed_tracked_sites.py  # Database seeding ✅
│           └── __init__.py
├── frontend/
│   ├── index.html
│   └── src/                            # React components, API client, styles
├── test/
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
# Gemini API Configuration (Primary LLM)
GEMINI_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3-flash-preview

# Groq API Configuration (Fallback LLM)
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
```

### Setup Instructions
1. Copy `backend/.env.example` to `backend/.env`
2. Add your Gemini API key from https://aistudio.google.com/apikey
3. (Optional) Add your Groq API key from https://console.groq.com/keys for fallback
4. Set `APP_DB_URL` to your PostgreSQL connection string (same DB as Airflow)
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

### Test Case 1: Basic Extraction (Multi-City)
**Input**: "I want to visit Toronto from March 15-17, 2026. Budget is $300. I'm interested in food and museums."
**Expected**: Extract city=Toronto, dates, budget ($100/day), interests [Food and Beverage, Culture and History]

### Test Case 2: Budget Validation
**Input**: "Planning 3-day trip with $100 total budget"
**Expected**: Calculate $33/day, reject with message about $50/day minimum

### Test Case 3: Itinerary with DB Venues
**Input**: Complete preferences for Toronto with interests [Culture and History]
**Expected**: ItineraryService queries Airflow DB for Toronto venues, includes them in prompt, generated activities have `from_database: true`

### Test Case 4: Graceful Degradation (No DB)
**Input**: Complete preferences for a city with no venues in DB
**Expected**: ItineraryService generates itinerary using Gemini's knowledge, no `from_database` flags

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

1. **Multi-city support**: The system works for any city. Do NOT hardcode city names.
2. **Never remove fields** from TripPreferences without understanding full impact
3. **Always validate** user inputs against minimum requirements before proceeding
4. **Be conservative** in extraction — only extract explicitly mentioned information
5. **Follow the layered architecture** — don't mix concerns between schemas, services, and clients
6. **Venue DB is optional** — the system must work even if PostgreSQL is unreachable
7. **Document changes** to schemas, APIs, or core logic in this CLAUDE.md file
8. **FastAPI async pattern** — service methods are async; sync I/O (Groq, SQLAlchemy) uses `run_in_executor`

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
- [ ] Seed database with Toronto venues
- [ ] Add Google Maps API for geocoding

### Phase 3: Advanced Features
- [ ] Multi-modal transportation planning
- [ ] Weather API integration
- [ ] Real-time budget tracking
- [ ] Schedule adaptation engine
- [ ] Expand Airflow scraping to more cities

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

# Run tests
pytest test/

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

**Last Updated**: 2026-02-07
**Phase**: Phase 2 Complete (FastAPI + Itinerary + Airflow DB)
**Next Steps**: Seed Toronto venues, add Google Maps geocoding, begin Phase 3 features
