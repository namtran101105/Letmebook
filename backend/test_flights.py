"""Quick test for the flight client."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from clients.flight_client import FlightClient


def main():
    client = FlightClient()

    result = client.search_flights(
        origin="Toronto, Ontario",
        destination="Montreal, Quebec",
        departure_date="2026-02-15",
        return_date="2026-02-25",
    )
    print(f"{result['origin']} ({result['origin_code']}) -> "
          f"{result['destination']} ({result['destination_code']})")
    print(f"  Depart: {result['departure_date']}")
    print(f"  Return: {result['return_date']}")
    print(f"  Direct link:   {result['skyscanner_link']}")
    print(f"  Referral link: {result['skyscanner_referral_link']}")


if __name__ == "__main__":
    main()
