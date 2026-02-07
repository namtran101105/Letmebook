# NLP Extraction Service Setup

This guide explains how to set up and use the NLP extraction service for extracting travel preferences from natural language.

## Overview

The NLP extraction service uses Google's Gemini AI to extract structured trip preferences from user messages. It can extract:

- **Travel dates** (start, end, duration)
- **Budget** (min, max, currency)
- **Interests** (activities, attractions)
- **Dietary restrictions**
- **Accessibility needs**
- **Group information** (size, traveling companions)
- **Accommodation preferences**
- **Transportation preferences**
- **Specific must-see or must-avoid places**

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
# GEMINI_API_KEY=your_actual_api_key_here
```

### 4. Test the Service

```bash
# From the travel-planner directory
python test_extraction.py
```

## Usage Examples

### Basic Extraction

```python
from services.nlp_extraction_service import NLPExtractionService

# Create service instance
service = NLPExtractionService()

# Extract preferences from user message
user_message = "I want to visit Kingston next weekend with my family. We love museums and food tours. Budget is $500."

preferences = service.extract_preferences(user_message)

# Access extracted data
print(f"Trip ID: {preferences.trip_id}")
print(f"Dates: {preferences.start_date} to {preferences.end_date}")
print(f"Budget: ${preferences.budget_min}-${preferences.budget_max}")
print(f"Interests: {preferences.interests}")
print(f"Group size: {preferences.group_size}")

# Convert to JSON
json_output = preferences.to_json()
print(json_output)
```

### Refining Preferences

```python
# User provides additional information
additional_info = "Actually, I'm vegetarian and want to see Fort Henry"

# Refine the existing preferences
refined = service.refine_preferences(preferences, additional_info)

print(f"Dietary: {refined.dietary_restrictions}")
print(f"Must see: {refined.must_see}")
```

### Validating Preferences

```python
# Validate extracted preferences
validation = service.validate_preferences(preferences)

print(f"Valid: {validation['valid']}")
print(f"Completeness: {validation['completeness_score']}")
print(f"Warnings: {validation['warnings']}")
print(f"Issues: {validation['issues']}")
```

## API Response Format

The service returns a `TripPreferences` object with the following structure:

```json
{
  "trip_id": "trip_20260207_123456_a3f2b1c4",
  "user_input": "Original user message...",
  "start_date": "2026-03-15",
  "end_date": "2026-03-17",
  "duration_days": 3,
  "budget_min": 500.0,
  "budget_max": 800.0,
  "budget_currency": "CAD",
  "interests": ["museums", "food tours", "hiking"],
  "activity_level": "moderate",
  "pace": "relaxed",
  "dietary_restrictions": ["vegetarian"],
  "accessibility_needs": [],
  "group_size": 4,
  "traveling_with": "family",
  "accommodation_type": "hotel",
  "must_see": ["Fort Henry"],
  "must_avoid": [],
  "transportation_preference": "walking",
  "weather_preference": null,
  "extracted_at": "2026-02-07T10:30:00.000000",
  "confidence_score": 0.85
}
```

## Key Features

### 1. **Intelligent Extraction**
- Uses Gemini AI with specialized prompts
- Only extracts explicitly mentioned information
- Provides confidence scores

### 2. **Preference Refinement**
- Can update preferences with additional user input
- Preserves existing information while incorporating new details

### 3. **Validation**
- Checks for logical consistency (dates, budget ranges)
- Calculates completeness score
- Returns warnings and issues

### 4. **Flexible Configuration**
- Adjustable temperature for extraction accuracy
- Configurable token limits
- Support for different Gemini models

## Configuration Options

Edit your `.env` file to customize:

```bash
# Model selection (flash is faster, pro is more accurate)
GEMINI_MODEL=gemini-2.0-flash-exp

# Extraction settings (lower temperature = more consistent)
EXTRACTION_TEMPERATURE=0.2
EXTRACTION_MAX_TOKENS=2048

# Itinerary generation settings
ITINERARY_TEMPERATURE=0.7
ITINERARY_MAX_TOKENS=4096
```

## Integration with Flask/FastAPI

See the following files for integration examples:
- `backend/routes/trip_routes.py` - API endpoints
- `backend/controllers/trip_controller.py` - Request handlers
- `backend/storage/trip_json_repo.py` - Data persistence

## Troubleshooting

### API Key Issues
```
ValueError: GEMINI_API_KEY environment variable is required
```
**Solution**: Make sure your `.env` file exists and contains a valid API key.

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
3. **Generate itinerary**: Use the extracted preferences to create trip schedules
4. **Add frontend**: Create UI for displaying extracted preferences

## Files Created

- ✅ [models/trip_preferences.py](backend/models/trip_preferences.py) - Data model
- ✅ [clients/gemini_client.py](backend/clients/gemini_client.py) - API client
- ✅ [services/nlp_extraction_service.py](backend/services/nlp_extraction_service.py) - Main service
- ✅ [config/settings.py](backend/config/settings.py) - Configuration
- ✅ [utils/id_generator.py](backend/utils/id_generator.py) - ID generation
- ✅ [.env.example](backend/.env.example) - Environment template
- ✅ [requirements.txt](backend/requirements.txt) - Dependencies

## Support

For questions or issues, refer to:
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- Project README.md (coming soon)
