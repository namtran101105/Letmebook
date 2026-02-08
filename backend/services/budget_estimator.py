"""
Budget estimator service.
Scrapes real Airbnb prices and estimates flight costs to check budget feasibility.
Returns Skyscanner and Airbnb links for booking.
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clients.flight_client import FlightClient
from clients.airbnb_client import AirbnbClient
from clients.busbud_client import BusbudClient


# ---------------------------------------------------------------------------
# Flight price estimates (CAD, round-trip per person)
# Skyscanner can't be scraped, so we use market-based estimates.
# ---------------------------------------------------------------------------

FLIGHT_ROUTE_PRICES = {
    ("kingston", "montreal"): (120, 250),
    ("kingston", "ottawa"): (110, 220),
    ("kingston", "toronto"): (110, 220),
    ("montreal", "ottawa"): (110, 200),
    ("montreal", "toronto"): (150, 300),
    ("ottawa", "toronto"): (140, 280),
    ("calgary", "vancouver"): (180, 350),
    ("calgary", "edmonton"): (120, 220),
    ("toronto", "vancouver"): (350, 650),
    ("toronto", "halifax"): (300, 550),
    ("montreal", "vancouver"): (350, 650),
}

FLIGHT_TIER_PRICES = {
    "domestic_short": (130, 270),
    "domestic_long": (350, 650),
    "us_short": (250, 500),
    "international": (700, 1400),
}

CANADIAN_CITIES = {
    "toronto", "montreal", "ottawa", "kingston", "vancouver", "calgary",
    "edmonton", "winnipeg", "hamilton", "quebec city", "london", "halifax",
    "niagara falls",
}
US_CITIES = {"new york", "new york city", "boston", "chicago", "miami"}

DOMESTIC_SHORT_PAIRS = {
    frozenset(p) for p in [
        ("toronto", "montreal"), ("toronto", "ottawa"), ("toronto", "kingston"),
        ("toronto", "hamilton"), ("toronto", "london"), ("toronto", "niagara falls"),
        ("montreal", "ottawa"), ("montreal", "quebec city"),
        ("ottawa", "kingston"), ("ottawa", "montreal"),
        ("calgary", "edmonton"),
    ]
}


class BudgetEstimator:
    """Estimates trip costs using real Airbnb prices and flight estimates."""

    def __init__(self):
        self.flight_client = FlightClient()
        self.airbnb_client = AirbnbClient()
        self.busbud_client = BusbudClient()

    def estimate(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        budget: float,
        adults: int = 1,
    ) -> Dict[str, Any]:
        """
        Estimate trip cost using scraped Airbnb prices + flight estimates.

        Args:
            origin: Origin city.
            destination: Destination city.
            departure_date: YYYY-MM-DD.
            return_date: YYYY-MM-DD.
            budget: Total trip budget in CAD.
            adults: Number of travelers.

        Returns:
            Dict with cost breakdown, budget status, and booking links.
        """
        nights = (
            datetime.strptime(return_date, "%Y-%m-%d")
            - datetime.strptime(departure_date, "%Y-%m-%d")
        ).days
        if nights <= 0:
            raise ValueError("Return date must be after departure date")

        # --- Scrape real Airbnb prices ---
        airbnb_data = self.airbnb_client.scrape_prices(
            destination, departure_date, return_date, adults
        )
        airbnb_scraped = airbnb_data["listings_found"] > 0

        if airbnb_scraped:
            airbnb_low = airbnb_data["lowest_nightly"]
            airbnb_high = airbnb_data["highest_nightly"]
            airbnb_avg = airbnb_data["average_nightly"]
        else:
            airbnb_low = airbnb_high = airbnb_avg = None

        # --- Estimate flight prices ---
        flight_low, flight_high = self._get_flight_prices(origin, destination)

        # --- Calculate totals ---
        # Cheapest possible
        total_flight_low = flight_low
        total_airbnb_low = (airbnb_low or 0) * nights
        total_low = total_flight_low + total_airbnb_low

        # Most expensive
        total_flight_high = flight_high
        total_airbnb_high = (airbnb_high or 0) * nights
        total_high = total_flight_high + total_airbnb_high

        # Average / recommended
        flight_mid = round((flight_low + flight_high) / 2)
        airbnb_mid = airbnb_avg or 0
        total_flight_mid = flight_mid
        total_airbnb_mid = round(airbnb_mid * nights, 2)
        total_mid = total_flight_mid + total_airbnb_mid

        # Budget check
        if total_low <= budget:
            within_budget = True
        else:
            within_budget = False

        # Generate links
        flight_result = self.flight_client.search_flights(
            origin, destination, departure_date, return_date
        )

        # Bus/train as alternative (not all cities supported)
        busbud_bus = None
        busbud_train = None
        try:
            busbud_result = self.busbud_client.search_all(
                origin, destination, departure_date, return_date
            )
            busbud_bus = busbud_result["bus_link"]
            busbud_train = busbud_result["train_link"]
        except ValueError:
            pass

        return {
            "budget": budget,
            "within_budget": within_budget,
            "nights": nights,
            "adults": adults,
            "airbnb_prices_scraped": airbnb_scraped,
            "prices": {
                "flight_per_person": {
                    "low": flight_low,
                    "high": flight_high,
                    "source": "estimated",
                },
                "airbnb_per_night": {
                    "low": airbnb_low,
                    "high": airbnb_high,
                    "average": airbnb_avg,
                    "listings_found": airbnb_data["listings_found"],
                    "source": "scraped from Airbnb"
                    if airbnb_scraped
                    else "unavailable",
                },
            },
            "cheapest_total": {
                "flights": total_flight_low,
                "accommodation": total_airbnb_low,
                "total": total_low,
            },
            "average_total": {
                "flights": total_flight_mid,
                "accommodation": total_airbnb_mid,
                "total": total_mid,
            },
            "most_expensive_total": {
                "flights": total_flight_high,
                "accommodation": total_airbnb_high,
                "total": total_high,
            },
            "remaining_at_cheapest": budget - total_low,
            "remaining_at_average": budget - total_mid,
            "links": {
                "skyscanner": flight_result["skyscanner_link"],
                "skyscanner_referral": flight_result["skyscanner_referral_link"],
                "busbud_bus": busbud_bus,
                "busbud_train": busbud_train,
                "airbnb": airbnb_data["airbnb_link"],
            },
        }

    def _get_flight_prices(self, origin: str, destination: str) -> tuple:
        o = origin.split(",")[0].strip().lower()
        d = destination.split(",")[0].strip().lower()
        key = tuple(sorted([o, d]))
        if key in FLIGHT_ROUTE_PRICES:
            return FLIGHT_ROUTE_PRICES[key]
        tier = self._classify_route(o, d)
        return FLIGHT_TIER_PRICES[tier]

    @staticmethod
    def _classify_route(origin: str, destination: str) -> str:
        o_ca = origin in CANADIAN_CITIES
        d_ca = destination in CANADIAN_CITIES
        o_us = origin in US_CITIES
        d_us = destination in US_CITIES
        if o_ca and d_ca:
            if frozenset([origin, destination]) in DOMESTIC_SHORT_PAIRS:
                return "domestic_short"
            return "domestic_long"
        if (o_ca and d_us) or (o_us and d_ca):
            return "us_short"
        return "international"
