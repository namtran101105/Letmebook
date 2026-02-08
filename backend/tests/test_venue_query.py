"""Test querying venues from the database."""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.venue_service import VenueService

def test_venue_query():
    print("Testing VenueService...\n")
    
    service = VenueService()
    
    # Test 1: Query Toronto venues for Culture and History
    print("Test 1: Culture and History venues in Toronto")
    print("-" * 60)
    venues = service.get_venues_for_itinerary(
        city="Toronto",
        interests=["Culture and History"],
        budget_per_day=100.0
    )
    
    print(f"Found {len(venues)} venues:")
    for v in venues[:5]:  # Show first 5
        print(f"  - {v['name']} ({v.get('category', 'N/A')})")
        print(f"    Address: {v.get('address', 'N/A')}")
    
    print("\n" + "="*60 + "\n")
    
    # Test 2: Query for Food and Beverage
    print("Test 2: Food and Beverage venues in Toronto")
    print("-" * 60)
    venues = service.get_venues_for_itinerary(
        city="Toronto",
        interests=["Food and Beverage"],
        budget_per_day=150.0
    )
    
    print(f"Found {len(venues)} venues:")
    for v in venues:
        print(f"  - {v['name']} ({v.get('category', 'N/A')})")
    
    print("\n" + "="*60 + "\n")
    
    # Test 3: Query for multiple interests
    print("Test 3: Multiple interests (Culture + Food + Natural Place)")
    print("-" * 60)
    venues = service.get_venues_for_itinerary(
        city="Toronto",
        interests=["Culture and History", "Food and Beverage", "Natural Place"],
        budget_per_day=200.0
    )
    
    print(f"Found {len(venues)} venues:")
    categories = {}
    for v in venues:
        cat = v.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\nBreakdown by category:")
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count}")

if __name__ == "__main__":
    test_venue_query()
