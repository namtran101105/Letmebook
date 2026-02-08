"""
Client for Airbnb search links and price scraping.
No API key required.
"""

import re
from typing import Dict, Any, Optional
from urllib.parse import quote_plus

import httpx


class AirbnbClient:
    """Generates Airbnb search links and scrapes real listing prices."""

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

    def scrape_prices(
        self,
        destination: str,
        checkin: str,
        checkout: str,
        adults: int = 2,
    ) -> Dict[str, Any]:
        """
        Scrape real Airbnb nightly rates from search results.

        Args:
            destination: City or area.
            checkin: Check-in date YYYY-MM-DD.
            checkout: Check-out date YYYY-MM-DD.
            adults: Number of guests.

        Returns:
            Dict with lowest/highest/average nightly rates (CAD),
            listing count, and the Airbnb link.
        """
        search = self.search_stays(destination, checkin, checkout, adults)
        url = search["airbnb_link"]

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        try:
            resp = httpx.get(
                url, headers=headers, timeout=30, follow_redirects=True
            )
            html = resp.text

            # Airbnb embeds "N nights x $XX.XX CAD" in the HTML
            pattern = r'(\d+)\s*nights?\s*x\s*\$([\d,.]+)\s*CAD'
            matches = re.findall(pattern, html)

            rates = []
            for _, rate in matches:
                rates.append(float(rate.replace(",", "")))

            if rates:
                return {
                    "listings_found": len(rates),
                    "lowest_nightly": round(min(rates), 2),
                    "highest_nightly": round(max(rates), 2),
                    "average_nightly": round(sum(rates) / len(rates), 2),
                    "currency": "CAD",
                    "airbnb_link": url,
                }

        except Exception:
            pass

        return {
            "listings_found": 0,
            "lowest_nightly": None,
            "highest_nightly": None,
            "average_nightly": None,
            "currency": "CAD",
            "airbnb_link": url,
            "error": "Could not scrape prices",
        }
