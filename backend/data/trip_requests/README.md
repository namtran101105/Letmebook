# Trip Requests Directory

This directory stores completed trip preference JSON files.

## File Format

Each file is named: `trip_{city_name}_{timestamp}.json`

Example: `trip_tokyo_20260207_143025.json`

## Content Structure

Each JSON file contains:
- `city`: Destination city
- `country`: Destination country
- `start_date`: Trip start date (YYYY-MM-DD)
- `end_date`: Trip end date (YYYY-MM-DD)
- `duration_days`: Trip duration in days
- `budget`: Total budget
- `budget_currency`: Currency code (default: CAD)
- `interests`: Array of user interests
- `pace`: Travel pace (relaxed, moderate, packed)
- `location_preference`: Optional preferred location/area
- `_metadata`: File metadata (created_at, file_version)

## Automatic Creation

These files are automatically created when:
1. User completes all required preferences (100% completeness)
2. The chatbot confirms all information is collected

## Usage

These JSON files can be used for:
- Itinerary generation input
- Trip planning analysis
- Historical data/logging
- Testing and debugging
