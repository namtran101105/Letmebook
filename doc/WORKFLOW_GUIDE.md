# MonVoyage Conversational Toronto Itinerary - Workflow Guide

## Prerequisites

- **Python 3.8+**
- **Groq API key** (required) - Get one at https://console.groq.com/keys
- **PostgreSQL** (optional) - Only needed if you want Airflow-scraped venue data; the system falls back to a built-in Toronto venue list when the DB is unavailable

## Setup

### 1. Install dependencies

```bash
cd MonVoyage
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set at minimum:

```bash
GROQ_API_KEY=gsk_your_groq_api_key_here
```

Optional settings (all have sensible defaults):

```bash
GEMINI_KEY=              # Leave blank if using Groq only
GROQ_MODEL=llama-3.3-70b-versatile
HOST=127.0.0.1
PORT=8000
APP_DB_URL=postgresql+psycopg2://app:app@localhost:5432/app
```

### 3. Seed venues (optional, requires PostgreSQL)

If you have PostgreSQL running:

```bash
python airflow/dags/lib/seed_tracked_sites.py
```

This inserts 15 Toronto venues into the database. If PostgreSQL is not available, the system automatically uses the built-in fallback venue list.

## Starting the Server

```bash
python3 backend/app.py
```

Expected output:

```
Settings validated
Conversation Service initialized successfully
Starting server on http://127.0.0.1:8000
API docs at http://127.0.0.1:8000/docs
```

- **Chat UI**: http://localhost:8000
- **API docs**: http://localhost:8000/docs

## Conversation Flow

The assistant progresses through four phases:

```
greeting  ->  intake  ->  confirmed  ->  itinerary
```

### Phase 1: Greeting

The assistant introduces itself and asks how it can help plan a Toronto trip.

### Phase 2: Intake

The assistant collects four required pieces of information:

| Field | Example |
|-------|---------|
| **Travel dates** | March 15-17, 2026 |
| **Budget** | $300 CAD total |
| **Interests** | Museums, food, parks |
| **Pace** | Relaxed / Moderate / Packed |

After each turn, the assistant appends a `Still need:` line listing what information is still missing.

### Phase 3: Confirmation

Once all four fields are collected, the assistant summarizes what it knows and asks: "Want me to generate your Toronto itinerary now?"

### Phase 4: Itinerary

After the user confirms, the assistant generates a day-by-day itinerary using **only** venues from the venue database. Every activity includes a `Source: {venue_id}, {url}` citation.

## Example Conversation

**Turn 1** (automatic greeting on page load):
> Hi! I'm your Toronto Trip Planner. I'll help you build a personalized itinerary for Toronto, Canada. To get started, could you tell me your travel dates?
>
> Still need: travel dates, budget, interests, pace

**Turn 2** (user: "March 15-17, budget is $300"):
> Great! A 3-day trip from March 15-17 with a $300 budget - that's about $100/day, which gives us good options. What kinds of activities interest you? For example: museums, food tours, parks, sports, culture, entertainment...
>
> Still need: interests, pace

**Turn 3** (user: "I love museums and food. Moderate pace please"):
> Perfect! Here's what I have:
> - Dates: March 15-17, 2026
> - Budget: $300 CAD
> - Interests: Museums, Food
> - Pace: Moderate
>
> Want me to generate your Toronto itinerary now?

**Turn 4** (user: "Yes, let's do it!"):
> Day 1 - March 15
> Morning: Visit the Royal Ontario Museum (Source: rom, https://www.rom.on.ca)
> Afternoon: Lunch at St. Lawrence Market (Source: st_lawrence_market, https://www.stlawrencemarket.com)
> Evening: Explore the Distillery Historic District (Source: distillery_district, https://www.thedistillerydistrict.com)
>
> Day 2 - March 16
> ...

## Testing via cURL

### Health check

```bash
curl http://localhost:8000/api/health
```

### Greeting (empty messages)

```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": []}' | python3 -m json.tool
```

Expected: `phase: "greeting"`, a welcome message, and `still_need` listing all four fields.

### Intake turn

Use the `messages` array from the greeting response:

```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "..."},
      {"role": "assistant", "content": "...greeting..."}
    ],
    "user_input": "I want to visit March 15-17, budget $300, love museums and food, moderate pace"
  }' | python3 -m json.tool
```

Expected: `phase` is `"intake"` or `"confirmed"` depending on how much info was provided. `still_need` lists remaining fields (or is empty).

### Confirm and generate

When the assistant asks for confirmation, send an affirmative:

```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [...full message history...],
    "user_input": "Yes, generate it!"
  }' | python3 -m json.tool
```

Expected: `phase: "itinerary"`, the `assistant_message` contains a day-by-day plan with `Source:` lines.

### Testing via browser

1. Open http://localhost:8000
2. The greeting appears automatically
3. Type your trip details in the chat input
4. Continue the conversation until the itinerary is generated
5. The right panel shows:
   - During intake: "What I know so far" checklist
   - After itinerary: Formatted day-by-day plan

## QA Verification Checklist

### Intake phase

- [ ] Every assistant response during intake ends with `Still need: <list>`
- [ ] The `still_need` field in the API response matches the line in the message
- [ ] Fields disappear from `still_need` as the user provides them
- [ ] The right panel shows green checkmarks for collected fields and yellow badges for missing ones

### Confirmation gate

- [ ] When all four fields are collected, the assistant asks for confirmation (message contains "generate your Toronto itinerary")
- [ ] The itinerary is NOT generated until the user explicitly confirms (yes, sure, go ahead, etc.)
- [ ] Non-affirmative responses ("wait", "actually change the dates") keep the conversation in intake phase

### Itinerary generation

- [ ] Every Morning/Afternoon/Evening line includes `Source: {venue_id}, {url}`
- [ ] Every `venue_id` in the output matches a venue from the venue list (closed-world)
- [ ] Every `url` in the output matches the venue's actual source URL
- [ ] The itinerary respects the requested number of days
- [ ] The itinerary respects the requested pace (2-3 activities/day for relaxed, 4-5 for moderate, 6-8 for packed)

### Negative test (closed-world enforcement)

- [ ] If the user asks for a venue not in the list (e.g., "Include the Eiffel Tower"), the assistant refuses and suggests alternatives from the venue list
- [ ] No invented venues appear in the itinerary

### Legacy endpoints

- [ ] `GET /api/health` still works
- [ ] `POST /api/extract` still works (if GEMINI_KEY is configured)
- [ ] `POST /api/refine` still works (if GEMINI_KEY is configured)
- [ ] `POST /api/generate-itinerary` still works (if GEMINI_KEY is configured)

## Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| PostgreSQL unreachable | Uses `TORONTO_FALLBACK_VENUES` (15 built-in venues) |
| `GEMINI_KEY` not set | Chat endpoint works (Groq only); legacy extract/refine/generate endpoints return 500 |
| `GROQ_API_KEY` not set | Chat endpoint returns 503; legacy endpoints still work if GEMINI_KEY is set |
| Both keys missing | Server refuses to start with configuration error |

## Adding More Venues

### Option A: Add to the fallback list (no DB required)

Edit `backend/services/venue_service.py` and add entries to `TORONTO_FALLBACK_VENUES`:

```python
{
    "place_key": "your_venue_key",
    "name": "Venue Name",
    "category": "tourism",  # tourism, museum, food, entertainment, park, culture, sport
    "address": "123 Street, Toronto, ON",
    "description": "Brief description of the venue.",
    "source_url": "https://www.venue-website.com",
},
```

### Option B: Add to the database (requires PostgreSQL + Airflow)

1. Edit `airflow/dags/lib/seed_tracked_sites.py`
2. Add entries to both `PLACES` and `PAGES` lists
3. Run `python airflow/dags/lib/seed_tracked_sites.py`
4. Optionally trigger the Airflow DAG to scrape the venue website

## Available Toronto Venues (built-in)

| Venue ID | Name | Category |
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
