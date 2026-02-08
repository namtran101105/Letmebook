# MonVoyage Trip Planner

An AI-powered itinerary engine that generates feasible, day-by-day travel plans for any city worldwide. Built with FastAPI, Gemini AI, Apache Airflow, and PostgreSQL.

## Features

- **Natural Language Input** - Describe your trip in plain English; the AI extracts dates, budget, interests, and preferences automatically
- **Multi-City Support** - Works for any city (Toronto, Paris, Tokyo, etc.) with configurable defaults
- **Real Venue Data** - Airflow pipeline scrapes venue websites daily; itineraries use verified, up-to-date venue information
- **Smart Itinerary Generation** - Gemini AI creates day-by-day timetables respecting budget, pace, and interest constraints
- **Feasibility Validation** - Every itinerary is checked for schedule conflicts, budget overruns, and missing meals
- **Conversational Refinement** - Multi-turn chat to progressively build complete trip preferences
- **Auto-Generated API Docs** - Swagger UI and ReDoc available out of the box

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url> && cd MonVoyage

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your GEMINI_KEY

# 5. Start the server
python backend/app.py
```

Open http://localhost:8000 for the chat UI, or http://localhost:8000/docs for the API reference.

## Architecture

```
User (chat UI)
    |
    v
FastAPI (app.py)  ------>  Swagger UI (/docs)
    |
    +---> NLPExtractionService (Gemini/Groq)
    |         |
    |         v
    |     TripPreferences (validated)
    |
    +---> ItineraryService
    |         |
    |         +--- VenueService ---> PostgreSQL (Airflow DB)
    |         |
    |         +--- GeminiClient ---> Gemini API
    |         |
    |         v
    |     Itinerary (day-by-day timetable)
    |
    +---> Airflow DAGs (daily web scraping)
              |
              v
          PostgreSQL (places, tracked_pages, snapshots)
```

### Service Responsibilities

| Service | Role |
|---------|------|
| **NLPExtractionService** | Extracts structured trip preferences from natural language via Gemini (primary) or Groq (fallback) |
| **ItineraryService** | Generates day-by-day itineraries using Gemini AI + real venue data from the Airflow database |
| **VenueService** | Queries the Airflow-managed PostgreSQL database for venue information matching the user's city and interests |
| **GeminiClient** | Async wrapper for the Google Gemini API |
| **GroqClient** | Sync wrapper for the Groq API (fallback LLM) |

## API Reference

All endpoints return JSON. Auto-generated docs are at `/docs` (Swagger) and `/redoc` (ReDoc).

### `GET /api/health`

Returns service status and active LLM configuration.

```bash
curl http://localhost:8000/api/health
```

```json
{
  "status": "healthy",
  "service": "MonVoyage Trip Planner",
  "primary_llm": "gemini",
  "model": "Gemini (gemini-3-flash-preview)",
  "nlp_service_ready": true,
  "error": null
}
```

### `POST /api/extract`

Extract trip preferences from a natural language message.

```bash
curl -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"user_input": "I want to visit Toronto from March 15-17, 2026. Budget $300. Museums and food."}'
```

```json
{
  "success": true,
  "preferences": {
    "city": "Toronto",
    "country": "Canada",
    "start_date": "2026-03-15",
    "end_date": "2026-03-17",
    "budget": 300.0,
    "budget_currency": "CAD",
    "interests": ["Culture and History", "Food and Beverage"],
    "pace": "moderate"
  },
  "validation": {
    "valid": false,
    "issues": ["Missing: location_preference"],
    "warnings": [],
    "completeness_score": 0.8
  },
  "bot_message": "Great choice! Where in Toronto would you prefer to stay?",
  "saved_to_file": null
}
```

### `POST /api/refine`

Refine previously extracted preferences with additional user input.

```bash
curl -X POST http://localhost:8000/api/refine \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {"city": "Toronto", "country": "Canada", "budget": 300},
    "additional_input": "I prefer downtown and I am vegetarian"
  }'
```

### `POST /api/generate-itinerary`

Generate a complete day-by-day itinerary from finalized preferences. Requires all 10 mandatory fields.

```bash
curl -X POST http://localhost:8000/api/generate-itinerary \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {
      "city": "Toronto",
      "country": "Canada",
      "location_preference": "downtown",
      "start_date": "2026-03-15",
      "end_date": "2026-03-17",
      "duration_days": 3,
      "budget": 300.0,
      "budget_currency": "CAD",
      "interests": ["Culture and History", "Food and Beverage"],
      "pace": "moderate"
    }
  }'
```

```json
{
  "success": true,
  "itinerary": {
    "trip_id": "TRIP-20260215-abc123",
    "days": [
      {
        "day_number": 1,
        "date": "2026-03-15",
        "activities": [
          {
            "activity_id": "ACT-001",
            "venue_name": "Royal Ontario Museum",
            "planned_start": "09:30",
            "planned_end": "11:30",
            "category": "Culture and History",
            "estimated_cost": 23.0,
            "from_database": true
          }
        ]
      }
    ]
  },
  "feasibility": {
    "feasible": true,
    "issues": [],
    "warnings": []
  }
}
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_KEY` | Yes | — | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-3-flash-preview` | Gemini model name |
| `GROQ_API_KEY` | No | — | Groq API key (fallback LLM) |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model name |
| `HOST` | No | `127.0.0.1` | Server bind address |
| `PORT` | No | `8000` | Server port |
| `DEBUG` | No | `True` | Enable hot reload |
| `APP_DB_URL` | No | `postgresql+psycopg2://app:app@localhost:5432/app` | Airflow venue database URL |
| `DEFAULT_CITY` | No | `Toronto` | Default city for NLP extraction |
| `DEFAULT_COUNTRY` | No | `Canada` | Default country |
| `EXTRACTION_TEMPERATURE` | No | `0.2` | Gemini temperature for NLP extraction |
| `ITINERARY_TEMPERATURE` | No | `0.7` | Gemini temperature for itinerary generation |

### API Keys

1. **Gemini** (required): Get a key at https://aistudio.google.com/apikey
2. **Groq** (optional fallback): Get a key at https://console.groq.com/keys

## Airflow Venue Pipeline

The Airflow pipeline scrapes venue websites daily and stores structured data in PostgreSQL. The FastAPI backend reads this data to inject real venues into AI-generated itineraries.

### Setup

```bash
# 1. Start PostgreSQL
docker-compose -f docker-compose.dev.yml up -d postgres

# 2. Seed venues for your target city
python airflow/dags/lib/seed_tracked_sites.py

# 3. Start Airflow
airflow standalone

# 4. Enable the DAG in the Airflow UI
# Navigate to http://localhost:8080 and toggle "website_change_monitor"
```

### How It Works

1. **Airflow DAGs** scrape venue websites daily via the `website_change_monitor` DAG
2. Scraped data is stored in PostgreSQL: `places`, `tracked_pages`, `page_snapshots`, `place_facts`, `change_events`
3. **VenueService** queries these tables to find venues matching the user's city and interests
4. Venue data is injected into the Gemini prompt so the AI uses verified, real venues
5. Activities sourced from the database are tagged with `from_database: true`

### Graceful Degradation

If PostgreSQL is unreachable, the itinerary service still works. It generates itineraries using Gemini's general knowledge without real venue data.

## Project Structure

```
MonVoyage/
├── backend/
│   ├── app.py                   # FastAPI application (uvicorn, port 8000)
│   ├── config/settings.py       # Centralized configuration
│   ├── schemas/api_models.py    # Pydantic request/response schemas
│   ├── models/
│   │   ├── trip_preferences.py  # TripPreferences dataclass
│   │   └── itinerary.py         # Itinerary + Activity dataclasses
│   ├── services/
│   │   ├── nlp_extraction_service.py   # NLP preference extraction (async)
│   │   ├── itinerary_service.py        # Itinerary generation (async)
│   │   └── venue_service.py            # Airflow DB venue queries
│   ├── clients/
│   │   ├── gemini_client.py     # Gemini API wrapper (async)
│   │   └── groq_client.py       # Groq API wrapper (sync)
│   ├── utils/id_generator.py    # Trip/itinerary ID generation
│   └── .env.example             # Environment variable template
├── airflow/dags/
│   ├── website_monitor_dag.py   # Daily web scraping DAG
│   └── lib/                     # DAG support modules
├── frontend/
│   └── index.html               # Chat UI (single-page app)
├── test/                        # Test and demo scripts
├── requirements.txt             # Python dependencies
├── CLAUDE.md                    # AI assistant context
└── README.md                    # This file
```

## Development

```bash
# Format code
black backend/

# Lint code
flake8 backend/

# Run tests
pytest test/

# Run with verbose logging
LOG_LEVEL=DEBUG python backend/app.py
```

## Tech Stack

- **Backend**: FastAPI + uvicorn (async Python)
- **AI/NLP**: Google Gemini API (primary), Groq API (fallback)
- **Validation**: Pydantic v2
- **Database**: PostgreSQL + SQLAlchemy
- **Data Pipeline**: Apache Airflow
- **Vector Search**: Chroma (RAG retrieval)
- **Frontend**: Vanilla HTML/CSS/JS (chat interface)

## License

MIT
