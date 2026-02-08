"""Quick test for the budget estimator using trip preferences."""

import sys
import os
import json
from glob import glob

sys.path.insert(0, os.path.dirname(__file__))

from services.trip_budget_service import TripBudgetService
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
    print("BUDGET ESTIMATOR - Testing with Real Trip Preferences")
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
    print(f"  Booking Type: {preferences.booking_type}")
    if preferences.source_location:
        print(f"  Traveling From: {preferences.source_location}")
    print()
    
    # Initialize budget service
    service = TripBudgetService()
    
    # Estimate budget
    result = service.estimate_trip_budget(preferences)
    
    # Display results
    print("\n" + service.get_budget_summary(result))
    
    # Display quick status
    if not result.get("error"):
        print("\n📊 Budget Overview:")
        print("-" * 80)
        print(service.get_budget_status_summary(result))
        print()
    
    print("\n" + "=" * 80)
    print("✅ Budget estimation completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
