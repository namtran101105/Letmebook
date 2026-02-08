"""Quick test for the weather service using trip preferences."""

import sys
import os
import json
from glob import glob

sys.path.insert(0, os.path.dirname(__file__))

from services.weather_service import WeatherService
from models.trip_preferences import TripPreferences


def load_latest_trip_preferences() -> TripPreferences:
    """Load the most recent trip preferences JSON file."""
    # Try multiple possible paths (running from backend/ or from project root)
    search_paths = [
        "data/trip_requests/trip_*.json",  # Running from backend/
        "backend/data/trip_requests/trip_*.json",  # Running from project root
    ]
    
    trip_files = []
    for pattern in search_paths:
        found = glob(pattern)
        if found:
            trip_files = found
            break
    
    if not trip_files:
        raise FileNotFoundError("No trip preferences found in data/trip_requests/ or backend/data/trip_requests/")
    
    latest_file = max(trip_files, key=os.path.getmtime)
    print(f"📂 Loading: {latest_file}\n")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
        # Remove metadata if present
        data.pop('_metadata', None)
        return TripPreferences.from_dict(data)


def main():
    print("=" * 80)
    print("WEATHER SERVICE - Testing with Real Trip Preferences")
    print("=" * 80)
    
    # Load preferences
    try:
        preferences = load_latest_trip_preferences()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("Please run the chatbot first to generate trip preferences.")
        return
    
    # Display loaded preferences
    print("\n📋 Trip Preferences Loaded:")
    print("-" * 80)
    print(f"  Destination: {preferences.city}, {preferences.country}")
    print(f"  Dates: {preferences.start_date} to {preferences.end_date}")
    print(f"  Budget: ${preferences.budget} {preferences.budget_currency}")
    print(f"  Interests: {', '.join(preferences.interests) if preferences.interests else 'None'}")
    print(f"  Pace: {preferences.pace}")
    print()
    
    # Initialize weather service
    service = WeatherService()
    
    # Get weather forecast
    result = service.get_trip_weather(preferences)
    
    # Display results
    print("\n" + service.get_weather_summary(result))
    
    # Display quick summary
    if not result.get("error"):
        print("\n📊 Weather Overview:")
        print("-" * 80)
        print(service.get_weather_conditions_summary(result))
        print()
    
    print("\n" + "=" * 80)
    print("✅ Weather forecast completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
