"""Test that shows exactly what happens during venue fetching."""
import asyncio
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.itinerary_service import ItineraryService

async def test_venue_fetch():
    service = ItineraryService()
    
    preferences = {
        "city": "Toronto",
        "interests": ["Culture and History", "Food and Beverage"],
        "budget": 300.0,
        "duration_days": 3,
    }
    
    print("Fetching venues for Toronto with interests: Culture and History, Food and Beverage")
    print("-" * 80)
    
    venues = await service._fetch_venues(preferences)
    
    print(f"\n✅ Fetched {len(venues)} venues from database:\n")
    
    for v in venues:
        print(f"   - {v['name']}")
        print(f"     Category: {v.get('category', 'N/A')}")
        print(f"     Address: {v.get('address', 'N/A')}")
        print()

if __name__ == "__main__":
    asyncio.run(test_venue_fetch())
