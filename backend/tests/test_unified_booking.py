"""
Test the unified booking service with real trip preferences from JSON.
This script loads the latest trip preferences and books based on booking_type.
"""
import sys
import os
import json
from glob import glob

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.booking_service import BookingService
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
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
        # Remove metadata if present
        data.pop('_metadata', None)
        return TripPreferences.from_dict(data)


def main():
    print("=" * 80)
    print("UNIFIED BOOKING SERVICE - Testing with Real Trip Preferences")
    print("=" * 80)
    
    # Load the latest trip preferences
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
    print(f"  Location: {preferences.location_preference}")
    print(f"  Booking Type: {preferences.booking_type}")
    if preferences.source_location:
        print(f"  Traveling From: {preferences.source_location}")
    print()
    
    # Initialize booking service
    service = BookingService()
    
    # Execute bookings based on booking_type
    print("\n🎯 Executing Bookings...")
    print("-" * 80)
    
    results = service.book_trip(preferences)
    
    # Display results
    print("\n" + "=" * 80)
    print("BOOKING RESULTS")
    print("=" * 80)
    print(service.get_booking_summary(results))
    
    # Display detailed results as JSON
    print("\n📄 Detailed Results (JSON):")
    print("-" * 80)
    
    # Clean up results for display
    display_results = {
        "booking_type": results.get("booking_type"),
        "skipped": results.get("skipped", False)
    }
    
    if results.get("accommodation"):
        display_results["accommodation"] = results["accommodation"]
    
    if results.get("transportation"):
        display_results["transportation"] = results["transportation"]
    
    print(json.dumps(display_results, indent=2))
    
    print("\n" + "=" * 80)
    print("✅ Booking process completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
