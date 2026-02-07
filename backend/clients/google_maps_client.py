"""
Client for Google Maps Directions API.
Fetches routes between two locations for different transportation modes.
"""

from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus

import httpx

from config.settings import settings


DIRECTIONS_API_URL = "https://maps.googleapis.com/maps/api/directions/json"

# Modes supported by Google Maps Directions API
TRAVEL_MODES = ["driving", "transit", "walking"]


class GoogleMapsClient:
    """Client for fetching directions between two places via Google Maps API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_API_KEY
        if not self.api_key:
            raise ValueError(
                "GOOGLE_MAPS_API_KEY is required. "
                "Get one at https://console.cloud.google.com/apis/credentials"
            )

    def get_directions(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
    ) -> Dict[str, Any]:
        """
        Fetch directions between two places for a single travel mode.

        Args:
            origin: Starting location (address or place name).
            destination: Ending location (address or place name).
            mode: One of "driving", "transit", "walking".

        Returns:
            Dict with route summary, steps, and a Google Maps link.
        """
        if mode not in TRAVEL_MODES:
            raise ValueError(f"mode must be one of {TRAVEL_MODES}, got '{mode}'")

        params = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "key": self.api_key,
        }

        resp = httpx.get(DIRECTIONS_API_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data["status"] != "OK":
            return {
                "mode": mode,
                "status": data["status"],
                "error": data.get("error_message", "No routes found."),
                "routes": [],
                "google_maps_link": self._build_maps_link(
                    origin, destination, mode
                ),
            }

        routes = self._parse_routes(data["routes"], mode)

        return {
            "mode": mode,
            "status": "OK",
            "routes": routes,
            "google_maps_link": self._build_maps_link(
                origin, destination, mode
            ),
        }

    def get_all_routes(
        self,
        origin: str,
        destination: str,
        modes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch directions for all requested travel modes.

        Args:
            origin: Starting location (address or place name).
            destination: Ending location (address or place name).
            modes: List of modes to query. Defaults to all three.

        Returns:
            Dict keyed by mode, each containing route details and a link.
        """
        modes = modes or TRAVEL_MODES

        results = {}
        for mode in modes:
            try:
                results[mode] = self.get_directions(origin, destination, mode)
            except httpx.HTTPStatusError as e:
                results[mode] = {
                    "mode": mode,
                    "status": "HTTP_ERROR",
                    "error": str(e),
                    "routes": [],
                    "google_maps_link": self._build_maps_link(
                        origin, destination, mode
                    ),
                }

        return {
            "origin": origin,
            "destination": destination,
            "results": results,
        }

    def get_multi_stop_routes(
        self,
        destinations: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Fetch transit routes between each consecutive pair in a list of destinations.

        Args:
            destinations: Ordered list of places to visit
                          (e.g. ["CN Tower", "Art Gallery of Ontario", "BMO Field"]).

        Returns:
            List of dicts, one per leg (A->B, B->C, etc.), each with
            transit route details and a Google Maps link for that pair.
        """
        if len(destinations) < 2:
            raise ValueError("Need at least 2 destinations")

        legs = []

        for i in range(len(destinations) - 1):
            origin = destinations[i]
            dest = destinations[i + 1]
            route_data = self.get_directions(origin, dest, mode="transit")

            leg: Dict[str, Any] = {
                "leg": i + 1,
                "origin": origin,
                "destination": dest,
                "status": route_data["status"],
                "google_maps_link": route_data["google_maps_link"],
            }

            if route_data["status"] == "OK" and route_data["routes"]:
                r = route_data["routes"][0]
                leg["distance"] = r["distance"]
                leg["duration"] = r["duration"]
                leg["steps"] = r["steps"]
            else:
                leg["error"] = route_data.get("error", "No route found")

            legs.append(leg)

        return legs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_routes(
        self, raw_routes: List[Dict], mode: str
    ) -> List[Dict[str, Any]]:
        """Parse the raw Google Maps routes into a cleaner structure."""
        parsed = []
        for route in raw_routes:
            leg = route["legs"][0]  # single origin→destination has one leg

            route_info: Dict[str, Any] = {
                "summary": route.get("summary", ""),
                "distance": leg["distance"]["text"],
                "duration": leg["duration"]["text"],
                "start_address": leg["start_address"],
                "end_address": leg["end_address"],
                "steps": self._parse_steps(leg["steps"], mode),
            }

            if "warnings" in route:
                route_info["warnings"] = route["warnings"]

            parsed.append(route_info)

        return parsed

    def _parse_steps(
        self, raw_steps: List[Dict], mode: str
    ) -> List[Dict[str, Any]]:
        """Parse individual navigation steps."""
        steps = []
        for step in raw_steps:
            info: Dict[str, Any] = {
                "instruction": step.get("html_instructions", ""),
                "distance": step["distance"]["text"],
                "duration": step["duration"]["text"],
                "travel_mode": step.get("travel_mode", mode).lower(),
            }

            # For transit, include line/vehicle details
            if "transit_details" in step:
                td = step["transit_details"]
                info["transit"] = {
                    "line_name": td["line"].get("short_name")
                    or td["line"].get("name", ""),
                    "vehicle_type": td["line"]["vehicle"]["type"],
                    "departure_stop": td["departure_stop"]["name"],
                    "arrival_stop": td["arrival_stop"]["name"],
                    "num_stops": td.get("num_stops"),
                    "departure_time": td["departure_time"].get("text"),
                    "arrival_time": td["arrival_time"].get("text"),
                }

            steps.append(info)

        return steps

    @staticmethod
    def _build_maps_link(origin: str, destination: str, mode: str) -> str:
        """Build a shareable Google Maps directions URL."""
        return (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={quote_plus(origin)}"
            f"&destination={quote_plus(destination)}"
            f"&travelmode={mode}"
        )

    @staticmethod
    def _build_multi_stop_link(destinations: List[str]) -> str:
        """Build a Google Maps URL with waypoints for the full trip."""
        origin = quote_plus(destinations[0])
        dest = quote_plus(destinations[-1])
        waypoints = "|".join(quote_plus(d) for d in destinations[1:-1])
        url = (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={origin}"
            f"&destination={dest}"
        )
        if waypoints:
            url += f"&waypoints={waypoints}"
        return url

    @staticmethod
    def _compute_totals(
        legs: List[Dict], modes: List[str]
    ) -> Dict[str, Dict[str, str]]:
        """Sum up distance (km) and duration (mins) across all legs per mode."""
        totals: Dict[str, Dict[str, float]] = {
            m: {"distance_km": 0.0, "duration_mins": 0.0} for m in modes
        }

        for leg in legs:
            for mode in modes:
                route_data = leg["routes"].get(mode)
                if not route_data or route_data["status"] != "OK" or not route_data["routes"]:
                    continue
                r = route_data["routes"][0]
                # Parse "X.Y km" or "X m" -> km
                dist_text = r["distance"]
                if "km" in dist_text:
                    totals[mode]["distance_km"] += float(dist_text.replace("km", "").strip())
                elif "m" in dist_text:
                    totals[mode]["distance_km"] += float(dist_text.replace("m", "").strip()) / 1000
                # Parse "X mins" or "X hours Y mins" -> minutes
                dur_text = r["duration"]
                mins = 0.0
                if "hour" in dur_text:
                    parts = dur_text.split("hour")
                    mins += float(parts[0].strip()) * 60
                    rest = parts[1].replace("s", "").strip()
                    if "min" in rest:
                        mins += float(rest.replace("min", "").strip())
                elif "min" in dur_text:
                    mins += float(dur_text.replace("mins", "").replace("min", "").strip())
                totals[mode]["duration_mins"] += mins

        # Format into readable strings
        formatted: Dict[str, Dict[str, str]] = {}
        for mode in modes:
            km = totals[mode]["distance_km"]
            mins = totals[mode]["duration_mins"]
            hours = int(mins // 60)
            remaining = int(mins % 60)
            dur_str = f"{hours}h {remaining}min" if hours else f"{remaining} mins"
            formatted[mode] = {
                "total_distance": f"{km:.1f} km",
                "total_duration": dur_str,
            }
        return formatted
