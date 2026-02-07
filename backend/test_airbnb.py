"""Quick test for the Airbnb client."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from clients.airbnb_client import AirbnbClient


def main():
    client = AirbnbClient()

    result = client.search_stays(
        destination="Toronto, Ontario, Canada",
        checkin="2026-02-15",
        checkout="2026-02-20",
        adults=2,
    )

    print(f"Destination: {result['destination']}")
    print(f"  Check-in:  {result['checkin']}")
    print(f"  Check-out: {result['checkout']}")
    print(f"  Guests:    {result['adults']}")
    print(f"  Link:      {result['airbnb_link']}")


if __name__ == "__main__":
    main()
