"""Quick test for the Busbud bus/train client."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from clients.busbud_client import BusbudClient


def main():
    client = BusbudClient()

    result = client.search_all(
        origin="Toronto",
        destination="Montreal",
        departure_date="2026-02-15",
        return_date="2026-02-20",
    )

    print(f"{result['origin']} -> {result['destination']}")
    print(f"  Depart: {result['departure_date']}")
    print(f"  Return: {result['return_date']}")
    print(f"  Bus link:   {result['bus_link']}")
    print(f"  Train link: {result['train_link']}")

    print()

    result2 = client.search_all(
        origin="Toronto",
        destination="Montreal",
        departure_date="2026-03-01",
        return_date="2026-03-05",
    )

    print(f"{result2['origin']} -> {result2['destination']}")
    print(f"  Depart: {result2['departure_date']}")
    print(f"  Return: {result2['return_date']}")
    print(f"  Bus link:   {result2['bus_link']}")
    print(f"  Train link: {result2['train_link']}")


if __name__ == "__main__":
    main()
