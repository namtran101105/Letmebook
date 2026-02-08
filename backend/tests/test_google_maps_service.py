"""Test the Google Maps service with sample itinerary routes."""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.google_maps_service import GoogleMapsService


def test_single_route():
    """Test getting a route between two venues."""
    print("="*80)
    print("TEST 1: Single Route Between Two Venues")
    print("="*80)
    
    service = GoogleMapsService()
    
    if not service.is_available():
        print("\n⚠️  Google Maps API not configured (GOOGLE_MAPS_API_KEY not set)")
        print("   Set the key in backend/.env to test this feature")
        return
    
    origin = "CN Tower, Toronto, ON"
    destination = "Royal Ontario Museum, Toronto, ON"
    
    print(f"\nOrigin: {origin}")
    print(f"Destination: {destination}")
    print(f"Mode: transit\n")
    
    route = service.get_route_between_venues(origin, destination, mode="transit")
    
    if route["status"] == "OK" and route["routes"]:
        r = route["routes"][0]
        print(f"✅ Route found!")
        print(f"   Distance: {r['distance']}")
        print(f"   Duration: {r['duration']}")
        print(f"   Steps: {len(r['steps'])}")
        
        # Show transit details
        for step in r["steps"]:
            if "transit" in step:
                t = step["transit"]
                print(f"\n   🚇 {t['vehicle_type']} {t['line_name']}")
                print(f"      From: {t['departure_stop']}")
                print(f"      To: {t['arrival_stop']}")
                print(f"      Stops: {t['num_stops']}")
        
        print(f"\n   🔗 Google Maps: {route['google_maps_link']}")
    else:
        print(f"❌ No route found: {route.get('error', 'Unknown error')}")
        print(f"   Link: {route['google_maps_link']}")
    
    print()


def test_multiple_modes():
    """Test getting routes for all travel modes."""
    print("="*80)
    print("TEST 2: All Travel Modes")
    print("="*80)
    
    service = GoogleMapsService()
    
    if not service.is_available():
        print("\n⚠️  Google Maps API not configured")
        return
    
    origin = "CN Tower, Toronto"
    destination = "Art Gallery of Ontario, Toronto"
    
    print(f"\nOrigin: {origin}")
    print(f"Destination: {destination}\n")
    
    results = service.get_all_travel_modes(origin, destination)
    
    for mode, data in results["results"].items():
        print(f"\n{mode.upper()}:")
        print("-" * 40)
        
        if data["status"] == "OK" and data["routes"]:
            r = data["routes"][0]
            print(f"  Distance: {r['distance']}")
            print(f"  Duration: {r['duration']}")
        else:
            print(f"  ❌ {data.get('error', 'No route')}")
    
    print()


def test_itinerary_routes():
    """Test getting routes for a full itinerary with multiple stops."""
    print("="*80)
    print("TEST 3: Multi-Stop Itinerary Routes")
    print("="*80)
    
    service = GoogleMapsService()
    
    if not service.is_available():
        print("\n⚠️  Google Maps API not configured")
        return
    
    venues = [
        "CN Tower",
        "Royal Ontario Museum",
        "Art Gallery of Ontario",
        "St. Lawrence Market",
        "Distillery Historic District",
    ]
    
    print(f"\nPlanning routes for {len(venues)} venues in Toronto:\n")
    for i, venue in enumerate(venues, 1):
        print(f"   {i}. {venue}")
    
    print(f"\nFetching transit routes...\n")
    
    legs = service.get_itinerary_routes(
        venue_names=venues,
        city="Toronto",
        country="Canada",
        mode="transit"
    )
    
    if not legs:
        print("❌ No routes returned")
        return
    
    print(f"✅ Got {len(legs)} route legs:\n")
    
    for leg in legs:
        print(f"Leg {leg['leg']}: {leg['origin']} → {leg['destination']}")
        print("-" * 60)
        
        if leg["status"] != "OK":
            print(f"  ❌ No route: {leg.get('error', 'Unknown')}")
            print(f"  🔗 {leg['google_maps_link']}\n")
            continue
        
        print(f"  Distance: {leg['distance']}")
        print(f"  Duration: {leg['duration']}")
        
        # Show transit steps
        for step in leg.get("steps", []):
            if "transit" in step:
                t = step["transit"]
                print(f"  → {t['vehicle_type']} {t['line_name']}: "
                      f"{t['departure_stop']} → {t['arrival_stop']} "
                      f"({t['num_stops']} stops)")
        
        print(f"  🔗 {leg['google_maps_link']}\n")


def test_travel_time():
    """Test getting just the travel time in minutes."""
    print("="*80)
    print("TEST 4: Travel Time Calculation")
    print("="*80)
    
    service = GoogleMapsService()
    
    if not service.is_available():
        print("\n⚠️  Google Maps API not configured")
        return
    
    routes = [
        ("CN Tower, Toronto", "Royal Ontario Museum, Toronto", "transit"),
        ("CN Tower, Toronto", "Royal Ontario Museum, Toronto", "walking"),
        ("CN Tower, Toronto", "Toronto Islands, Toronto", "transit"),
    ]
    
    print()
    for origin, dest, mode in routes:
        travel_time = service.get_travel_time_minutes(origin, dest, mode)
        
        if travel_time:
            print(f"✅ {origin} → {dest} ({mode})")
            print(f"   Travel time: {travel_time} minutes\n")
        else:
            print(f"❌ {origin} → {dest} ({mode})")
            print(f"   No route found\n")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("GOOGLE MAPS SERVICE - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print()
    
    test_single_route()
    test_multiple_modes()
    test_itinerary_routes()
    test_travel_time()
    
    print("="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)
    print()


if __name__ == "__main__":
    main()
