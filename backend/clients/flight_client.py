"""
Client for generating Skyscanner flight search links.
No API key required — builds URLs that open Skyscanner
pre-filled with origin, destination, and dates.
"""

from typing import Dict, Any

# IATA codes for common cities. Skyscanner also accepts city names
# in the URL but IATA codes are more reliable.
IATA_CODES = {
    # Canada
    "toronto": "YTO",
    "ottawa": "YOW",
    "montreal": "YMQ",
    "vancouver": "YVR",
    "calgary": "YYC",
    "edmonton": "YEG",
    "winnipeg": "YWG",
    "halifax": "YHZ",
    "quebec city": "YQB",
    "kingston": "YGK",
    # USA
    "new york": "NYCA",
    "los angeles": "LAXA",
    "chicago": "CHIA",
    "san francisco": "SFO",
    "miami": "MIA",
    "boston": "BOS",
    "washington": "WASA",
    "seattle": "SEA",
    "las vegas": "LAS",
    "houston": "HOU",
    # Europe
    "london": "LOND",
    "paris": "PARI",
    "rome": "ROME",
    "barcelona": "BCN",
    "amsterdam": "AMS",
    "berlin": "BER",
    "dublin": "DUB",
    "lisbon": "LIS",
    "zurich": "ZRH",
    "vienna": "VIE",
    # Asia
    "tokyo": "TYOA",
    "seoul": "SEL",
    "bangkok": "BKK",
    "singapore": "SIN",
    "hong kong": "HKG",
    "hanoi": "HAN",
    "ho chi minh city": "SGN",
    "manila": "MNL",
    "kuala lumpur": "KUL",
    "taipei": "TPE",
    "beijing": "BJS",
    "shanghai": "SHA",
    "mumbai": "BOM",
    "delhi": "DEL",
    # Oceania
    "sydney": "SYD",
    "melbourne": "MEL",
    "auckland": "AKL",
    # South America
    "sao paulo": "SAO",
    "buenos aires": "BUE",
    "lima": "LIM",
    "bogota": "BOG",
    # Middle East / Africa
    "dubai": "DXB",
    "istanbul": "IST",
    "cairo": "CAI",
    "johannesburg": "JNB",
}


class FlightClient:
    """Generates Skyscanner flight search links."""

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
    ) -> Dict[str, Any]:
        """
        Generate a Skyscanner search link for a round-trip flight.

        Args:
            origin: Origin city (e.g. "Toronto" or "Ottawa, Ontario").
            destination: Destination city (e.g. "Hanoi" or "London").
            departure_date: Departure date in YYYY-MM-DD format.
            return_date: Return date in YYYY-MM-DD format.

        Returns:
            Dict with origin/destination codes, dates, and Skyscanner link.
        """
        origin_code = self._resolve_code(origin)
        dest_code = self._resolve_code(destination)

        # Convert YYYY-MM-DD -> YYMMDD for Skyscanner direct URL
        dep_short = departure_date[2:].replace("-", "")  # "2026-02-15" -> "260215"
        ret_short = return_date[2:].replace("-", "")

        # Direct URL: /transport/flights/{from}/{to}/{YYMMDD}/{YYMMDD}/
        direct_url = (
            f"https://www.skyscanner.ca/transport/flights/"
            f"{origin_code}/{dest_code}/{dep_short}/{ret_short}/"
        )

        # Referral URL (fallback, uses YYYY-MM-DD, more reliable)
        referral_url = (
            f"https://www.skyscanner.ca/g/referrals/v1/flights/day-view/"
            f"?origin={origin_code}&destination={dest_code}"
            f"&outboundDate={departure_date}"
            f"&inboundDate={return_date}"
        )

        return {
            "origin": origin,
            "origin_code": origin_code,
            "destination": destination,
            "destination_code": dest_code,
            "departure_date": departure_date,
            "return_date": return_date,
            "skyscanner_link": direct_url,
            "skyscanner_referral_link": referral_url,
        }

    def _resolve_code(self, city: str) -> str:
        """Resolve a city name to an IATA/Skyscanner code."""
        # Strip qualifiers like "Toronto, Ontario" -> "toronto"
        name = city.split(",")[0].strip().lower()

        if name in IATA_CODES:
            return IATA_CODES[name]

        # Fallback: use the city name as-is (Skyscanner can sometimes resolve it)
        return name
