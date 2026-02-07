"""
Client for generating Airbnb search links.
No API key required — builds URLs that open Airbnb
pre-filled with destination, dates, and guests.
"""

from typing import Dict, Any
from urllib.parse import quote_plus


class AirbnbClient:
    """Generates Airbnb accommodation search links."""

    def search_stays(
        self,
        destination: str,
        checkin: str,
        checkout: str,
        adults: int = 2,
    ) -> Dict[str, Any]:
        """
        Generate an Airbnb search link for accommodation.

        Args:
            destination: City or area (e.g. "Kingston, Ontario, Canada").
            checkin: Check-in date in YYYY-MM-DD format.
            checkout: Check-out date in YYYY-MM-DD format.
            adults: Number of adult guests (default 2).

        Returns:
            Dict with destination, dates, and Airbnb link.
        """
        query = quote_plus(destination)

        url = (
            f"https://www.airbnb.ca/s/{query}/homes"
            f"?checkin={checkin}"
            f"&checkout={checkout}"
            f"&adults={adults}"
        )

        return {
            "destination": destination,
            "checkin": checkin,
            "checkout": checkout,
            "adults": adults,
            "airbnb_link": url,
        }
