# NLP Extraction Service Setup

This guide explains how to set up and use the NLP extraction service for extracting travel preferences from natural language.

## Overview

The NLP extraction service uses Google's Gemini AI (primary) to extract structured trip preferences from user messages. It can extract:

- **Location** (city, country, location preference)
- **Travel dates** (start, end, duration)
- **Budget** (total budget, currency)
- **Interests** (activities, attractions — min 1, max 6)
- **Pace** (relaxed, moderate, packed)
- **Dietary restrictions** (optional)
- **Accessibility needs** (optional)
- **Group information** (size, group type — optional)
- **Transportation preferences** (optional, defaults to "mixed")
- **Specific must-see or must-avoid venues** (optional)

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Get API Key" or "Create API Key"
4. Copy your API key

### 3. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API key
# GEMINI_KEY=your_actual_api_key_here
```

### 4. Test the Service

```bash
# From the travel-planner directory
python backend/services/itinerary_service.py
```

## Usage Examples

### Basic Extraction

```python
from backend.services.nlp_extraction_service import NLPExtractionService

# Create service instance
service = NLPExtractionService()

# Extract preferences from user message
user_message = "I want to visit Kingston next weekend with my family. We love museums and food tours. Budget is $500."

preferences = service.extract_preferences(user_message)

# Access extracted data
print(f"City: {preferences.city}")
print(f"Country: {preferences.country}")
print(f"Dates: {preferences.start_date} to {preferences.end_date}")
print(f"Budget: ${preferences.budget} {preferences.budget_currency}")
print(f"Interests: {preferences.interests}")
print(f"Pace: {preferences.pace}")
print(f"Group size: {preferences.group_size}")

# Convert to dictionary
json_output = preferences.to_dict()
print(json_output)
```

### Refining Preferences

```python
# User provides additional information
additional_info = "Actually, I'm vegetarian and want to see Fort Henry"

# Refine the existing preferences
refined = service.refine_preferences(preferences, additional_info)

print(f"Dietary: {refined.dietary_restrictions}")
print(f"Must see: {refined.must_see_venues}")
```

### Validating Preferences

```python
# Validate extracted preferences
validation = preferences.validate()

print(f"Valid: {validation['valid']}")
print(f"Completeness: {validation['completeness_score']}")
print(f"Warnings: {validation['warnings']}")
print(f"Issues: {validation['issues']}")
```

## API Response Format

The service returns a `TripPreferences` object with the following structure:

```json
{
  "city": "Kingston",
  "country": "Canada",
  "location_preference": "City center near public transportation",
  "start_date": "2026-03-15",
  "end_date": "2026-03-17",
  "duration_days": 3,
  "budget": 500.0,
  "budget_currency": "CAD",
  "daily_budget": 166.67,
  "interests": ["museums", "food tours"],
  "pace": "moderate",
  "starting_location": "City center near public transportation",
  "hours_per_day": 8,
  "transportation_modes": ["mixed"],
  "group_size": 4,
  "group_type": "family",
  "children_ages": [],
  "dietary_restrictions": ["vegetarian"],
  "accessibility_needs": [],
  "weather_tolerance": null,
  "must_see_venues": ["Fort Henry"],
  "must_avoid_venues": [],
  "trip_id": null,
  "created_at": null,
  "updated_at": null
}
```

### Required Fields (10)

| Field | Type | Description |
|-------|------|-------------|
| `city` | str | Destination city (e.g., "Kingston") |
| `country` | str | Destination country (e.g., "Canada") |
| `location_preference` | str | Area preference (e.g., "City center near public transportation") |
| `start_date` | str | Trip start date (YYYY-MM-DD) |
| `end_date` | str | Trip end date (YYYY-MM-DD) |
| `duration_days` | int | Number of days (must match date range) |
| `budget` | float | Total trip budget |
| `budget_currency` | str | Currency code (e.g., "CAD") |
| `interests` | List[str] | Interest categories (min 1, max 6) |
| `pace` | str | Schedule pace: relaxed, moderate, or packed |

### Optional Fields (with defaults)

| Field | Type | Default |
|-------|------|---------|
| `starting_location` | str | Derived from `location_preference` |
| `hours_per_day` | int | 8 |
| `transportation_modes` | List[str] | ["mixed"] |
| `group_size` | int | None |
| `group_type` | str | None |
| `dietary_restrictions` | List[str] | [] |
| `accessibility_needs` | List[str] | [] |
| `weather_tolerance` | str | None |
| `must_see_venues` | List[str] | [] |
| `must_avoid_venues` | List[str] | [] |

## Key Features

### 1. **Intelligent Extraction**
- Uses Gemini AI (primary) with specialized prompts
- Groq API available as alternative/fallback
- Only extracts explicitly mentioned information
- Provides completeness scores

### 2. **Preference Refinement**
- Can update preferences with additional user input
- Preserves existing information while incorporating new details

### 3. **Validation**
- Checks for logical consistency (dates, budget, pace)
- Enforces $50/day minimum budget (non-negotiable)
- Calculates completeness score (0.0-1.0)
- Returns warnings and issues

### 4. **Flexible Configuration**
- Adjustable temperature for extraction accuracy
- Configurable token limits
- Support for different Gemini models

## Configuration Options

Edit your `.env` file to customize:

```bash
# Gemini API key (required)
GEMINI_KEY=your_api_key_here

# Model selection (flash is faster, pro is more accurate)
GEMINI_MODEL=gemini-2.0-flash

# Extraction settings (lower temperature = more consistent)
EXTRACTION_TEMPERATURE=0.2
EXTRACTION_MAX_TOKENS=2048

# Itinerary generation settings (higher temperature = more creative)
ITINERARY_TEMPERATURE=0.7
ITINERARY_MAX_TOKENS=8192

# Groq API (alternative/fallback LLM)
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

## Integration with FastAPI

See the following files for integration examples:
- `backend/routes/trip_routes.py` - API endpoints
- `backend/controllers/trip_controller.py` - Request handlers
- `backend/services/itinerary_service.py` - Itinerary generation
- `backend/storage/trip_json_repo.py` - Data persistence

## Troubleshooting

### API Key Issues
```
ValueError: Gemini API key required — set GEMINI_KEY in .env
```
**Solution**: Make sure your `.env` file exists and contains a valid `GEMINI_KEY`.

### Import Errors
```
ModuleNotFoundError: No module named 'dotenv'
```
**Solution**: Install dependencies: `pip install -r requirements.txt`

### JSON Parsing Errors
```
Failed to parse JSON response
```
**Solution**: Try increasing `EXTRACTION_TEMPERATURE` or using a different model.

## Next Steps

1. **Integrate with chatbot**: Use the service in your conversation flow
2. **Save to storage**: Use `trip_json_repo.py` to persist extracted preferences
3. **Generate itinerary**: Use `itinerary_service.py` to create trip timetables
4. **Add frontend**: Create UI for displaying extracted preferences and itineraries

## Files

- [models/trip_preferences.py](backend/models/trip_preferences.py) - Trip preferences data model
- [models/itinerary.py](backend/models/itinerary.py) - Itinerary data model
- [clients/gemini_client.py](backend/clients/gemini_client.py) - Gemini API client
- [services/nlp_extraction_service.py](backend/services/nlp_extraction_service.py) - NLP extraction service
- [services/itinerary_service.py](backend/services/itinerary_service.py) - Itinerary generation service
- [config/settings.py](backend/config/settings.py) - Configuration (Gemini + Groq)
- [utils/id_generator.py](backend/utils/id_generator.py) - ID generation
- [.env.example](backend/.env.example) - Environment template
- [requirements.txt](backend/requirements.txt) - Dependencies

## Support

For questions or issues, refer to:
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [Groq API Documentation](https://console.groq.com/docs)
- [Backend Documentation Index](backend/docs/README.md)
