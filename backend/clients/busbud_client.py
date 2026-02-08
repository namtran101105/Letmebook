"""
Client for generating Busbud bus/train search links.
No API key required — builds URLs that open Busbud
pre-filled with origin, destination, and dates.
"""

from typing import Dict, Any


# Busbud uses geohash codes in URLs. This maps city names to
# (slug, geohash) pairs scraped from busbud.com.
BUSBUD_CITIES = {
    # Canada
    "toronto": ("toronto", "dpz88g"),
    "montreal": ("montreal", "f25dvk"),
    "ottawa": ("ottawa", "f244m6"),
    "kingston": ("kingston", "drceee"),
    "vancouver": ("vancouver", "c2b2nm"),
    "calgary": ("calgary", "c3nf7v"),
    "edmonton": ("edmonton", "c3x29u"),
    "winnipeg": ("winnipeg", "cbfgv3"),
    "hamilton": ("hamilton", "dpxnnc"),
    "quebec city": ("quebec-city", "f2m673"),
    "london": ("london", "dpwhx2"),
    "halifax": ("halifax", "dxfvcr"),
    "niagara falls": ("niagara-falls", "dpxv0y"),
    # USA
    "new york": ("new-york-city", "dr5reg"),
    "new york city": ("new-york-city", "dr5reg"),
}


class BusbudClient:
    """Generates Busbud bus/train search links."""

    def search_bus(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
    ) -> Dict[str, Any]:
        """
        Generate a Busbud search link for bus tickets (round trip).

        Args:
            origin: Origin city (e.g. "Toronto" or "Kingston").
            destination: Destination city (e.g. "Montreal").
            departure_date: Departure date in YYYY-MM-DD format.
            return_date: Return date in YYYY-MM-DD format.

        Returns:
            Dict with city info, dates, and Busbud link.
        """
        origin_slug, origin_hash = self._resolve(origin)
        dest_slug, dest_hash = self._resolve(destination)

        url = (
            f"https://www.busbud.com/en-ca/"
            f"bus-{origin_slug}-{dest_slug}/r/{origin_hash}-{dest_hash}"
            f"?outbound_date={departure_date}&return_date={return_date}"
        )

        return {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "busbud_link": url,
        }

    def search_train(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
    ) -> Dict[str, Any]:
        """
        Generate a Busbud search link for train tickets (round trip).

        Args:
            origin: Origin city (e.g. "Toronto").
            destination: Destination city (e.g. "Montreal").
            departure_date: Departure date in YYYY-MM-DD format.
            return_date: Return date in YYYY-MM-DD format.

        Returns:
            Dict with city info, dates, and Busbud link.
        """
        origin_slug, origin_hash = self._resolve(origin)
        dest_slug, dest_hash = self._resolve(destination)

        url = (
            f"https://www.busbud.com/en-ca/"
            f"t/train-{origin_slug}-{dest_slug}/{origin_hash}-{dest_hash}"
            f"?outbound_date={departure_date}&return_date={return_date}"
        )

        return {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "busbud_link": url,
        }

    def search_all(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
    ) -> Dict[str, Any]:
        """
        Generate both bus and train Busbud links for a route.

        Returns:
            Dict with bus_link and train_link.
        """
        bus = self.search_bus(origin, destination, departure_date, return_date)
        train = self.search_train(origin, destination, departure_date, return_date)

        return {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "bus_link": bus["busbud_link"],
            "train_link": train["busbud_link"],
        }

    def _resolve(self, city: str) -> tuple:
        """Resolve a city name to a (slug, geohash) pair."""
        name = city.split(",")[0].strip().lower()

        if name in BUSBUD_CITIES:
            return BUSBUD_CITIES[name]

        # Fallback: generate slug from name, but geohash is unknown
        slug = name.replace(" ", "-")
        raise ValueError(
            f"City '{city}' not in Busbud lookup. "
            f"Supported cities: {', '.join(sorted(BUSBUD_CITIES.keys()))}"
        )
