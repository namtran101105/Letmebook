"""Quick test for the Google Maps directions client."""

import sys
import os

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from clients.google_maps_client import GoogleMapsClient


def main():
    destinations = [
        "CN Tower, Toronto, ON",
        "Art Gallery of Ontario, Toronto, ON",
        "BMO Field, Toronto, ON",
        "Yorkdale Shopping Centre, Toronto, ON",
        "Humber Bay Park, Toronto, ON",
    ]

    client = GoogleMapsClient()
    legs = client.get_multi_stop_routes(destinations)

    for leg in legs:
        print(f"\nLeg {leg['leg']}: {leg['origin']}  -->  {leg['destination']}")
        print("-" * 60)

        if leg["status"] != "OK":
            print(f"  No route found: {leg.get('error', '')}")
            print(f"  Link: {leg['google_maps_link']}")
            continue

        print(f"  Distance: {leg['distance']}")
        print(f"  Duration: {leg['duration']}")

        for step in leg["steps"]:
            if "transit" in step:
                t = step["transit"]
                print(f"  -> {t['vehicle_type']} {t['line_name']}: "
                      f"{t['departure_stop']} -> {t['arrival_stop']} "
                      f"({t['num_stops']} stops)")

        print(f"  Link: {leg['google_maps_link']}")


if __name__ == "__main__":
    main()
