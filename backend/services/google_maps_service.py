"""
Google Maps service for route planning and directions.

Provides high-level methods for getting routes between venues in an itinerary,
calculating travel times, and generating shareable Google Maps links.

Usage:
    from services.google_maps_service import GoogleMapsService
    
    service = GoogleMapsService()
    
    # Get routes between multiple destinations
    legs = service.get_itinerary_routes(
        ["CN Tower", "Royal Ontario Museum", "St. Lawrence Market"],
        city="Toronto",
        country="Canada"
    )
    
    # Get single route
    route = service.get_route_between_venues(
        "CN Tower, Toronto",
        "Art Gallery of Ontario, Toronto",
        mode="transit"
    )
"""

import logging
import sys
import os
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from clients.google_maps_client import GoogleMapsClient
from config.settings import settings

logger = logging.getLogger(__name__)


class GoogleMapsService:
    """Service for route planning and directions using Google Maps API."""

    def __init__(self, client: Optional[GoogleMapsClient] = None):
        """
        Initialize Google Maps service.
        
        Args:
            client: Optional GoogleMapsClient instance for dependency injection.
        """
        try:
            self.client = client or GoogleMapsClient()
            self._available = True
        except ValueError as e:
            logger.warning(f"Google Maps client unavailable: {e}")
            self._available = False
            self.client = None

    def is_available(self) -> bool:
        """Check if Google Maps API is configured and available."""
        return self._available

    def get_route_between_venues(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
    ) -> Dict[str, Any]:
        """
        Get route between two venues for a single travel mode.
        
        Args:
            origin: Starting location (address or place name)
            destination: Ending location (address or place name)
            mode: Travel mode - "driving", "transit", or "walking"
        
        Returns:
            Dict with route details including distance, duration, steps, and Google Maps link
        """
        if not self._available:
            return {
                "status": "UNAVAILABLE",
                "error": "Google Maps API not configured",
                "mode": mode,
                "google_maps_link": self._fallback_link(origin, destination, mode),
            }

        try:
            return self.client.get_directions(origin, destination, mode)
        except Exception as e:
            logger.error(f"Error getting route from {origin} to {destination}: {e}")
            return {
                "status": "ERROR",
                "error": str(e),
                "mode": mode,
                "google_maps_link": self._fallback_link(origin, destination, mode),
            }

    def get_all_travel_modes(
        self,
        origin: str,
        destination: str,
        modes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get routes for all requested travel modes between two venues.
        
        Args:
            origin: Starting location
            destination: Ending location
            modes: List of modes to query. Defaults to ["driving", "transit", "walking"]
        
        Returns:
            Dict with results for each mode
        """
        if not self._available:
            return {
                "origin": origin,
                "destination": destination,
                "status": "UNAVAILABLE",
                "error": "Google Maps API not configured",
            }

        try:
            return self.client.get_all_routes(origin, destination, modes)
        except Exception as e:
            logger.error(f"Error getting routes from {origin} to {destination}: {e}")
            return {
                "origin": origin,
                "destination": destination,
                "status": "ERROR",
                "error": str(e),
            }

    def get_itinerary_routes(
        self,
        venue_names: List[str],
        city: Optional[str] = None,
        country: Optional[str] = None,
        mode: str = "transit",
    ) -> List[Dict[str, Any]]:
        """
        Get transit routes for a complete itinerary with multiple stops.
        
        This method is designed to work with itinerary generation - it takes
        a list of venue names and returns route info for each consecutive pair.
        
        Args:
            venue_names: Ordered list of venue names to visit
            city: City name to append to each venue (e.g., "Toronto")
            country: Country name to append to each venue (e.g., "Canada")
            mode: Travel mode (default: "transit")
        
        Returns:
            List of route legs, one for each consecutive pair of venues
        
        Example:
            >>> service = GoogleMapsService()
            >>> venues = ["CN Tower", "Royal Ontario Museum", "St. Lawrence Market"]
            >>> legs = service.get_itinerary_routes(venues, city="Toronto", country="Canada")
            >>> for leg in legs:
            ...     print(f"Leg {leg['leg']}: {leg['distance']} in {leg['duration']}")
        """
        if not self._available:
            logger.warning("Google Maps API not available, returning empty routes")
            return []

        # Build full addresses
        destinations = []
        for venue in venue_names:
            address = venue
            if city:
                address += f", {city}"
            if country:
                address += f", {country}"
            destinations.append(address)

        try:
            if mode == "transit":
                # Use multi-stop routes for transit (optimized for public transport)
                return self.client.get_multi_stop_routes(destinations)
            else:
                # For other modes, get individual legs
                legs = []
                for i in range(len(destinations) - 1):
                    route_data = self.client.get_directions(
                        destinations[i],
                        destinations[i + 1],
                        mode=mode
                    )
                    
                    leg = {
                        "leg": i + 1,
                        "origin": destinations[i],
                        "destination": destinations[i + 1],
                        "status": route_data["status"],
                        "mode": mode,
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

        except Exception as e:
            logger.error(f"Error getting itinerary routes: {e}")
            return []

    def get_travel_time_minutes(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
    ) -> Optional[int]:
        """
        Get estimated travel time in minutes between two locations.
        
        Args:
            origin: Starting location
            destination: Ending location
            mode: Travel mode
        
        Returns:
            Travel time in minutes, or None if route not found
        """
        route = self.get_route_between_venues(origin, destination, mode)
        
        if route["status"] != "OK" or not route.get("routes"):
            return None
        
        # Parse duration text (e.g., "25 mins", "1 hour 15 mins")
        duration_text = route["routes"][0]["duration"]
        return self._parse_duration_to_minutes(duration_text)

    def enhance_itinerary_with_routes(
        self,
        itinerary: Dict[str, Any],
        city: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add route information to an existing itinerary.
        
        Takes an itinerary dict and adds route details (distance, duration, steps)
        between consecutive activities.
        
        Args:
            itinerary: Itinerary dict with 'days' containing activities
            city: City name for address resolution
            country: Country name for address resolution
        
        Returns:
            Enhanced itinerary with route information
        """
        if not self._available:
            logger.warning("Google Maps not available, returning itinerary unchanged")
            return itinerary

        enhanced = itinerary.copy()
        
        for day in enhanced.get("days", []):
            activities = day.get("activities", [])
            
            if len(activities) < 2:
                continue
            
            # Get venue names
            venue_names = [a["venue_name"] for a in activities]
            
            # Get routes
            routes = self.get_itinerary_routes(venue_names, city, country)
            
            # Add route info to activities
            for i, route in enumerate(routes):
                if i + 1 < len(activities):
                    activities[i]["route_to_next"] = {
                        "distance": route.get("distance", "N/A"),
                        "duration": route.get("duration", "N/A"),
                        "mode": route.get("mode", "transit"),
                        "google_maps_link": route.get("google_maps_link", ""),
                    }
        
        return enhanced

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_duration_to_minutes(duration_text: str) -> int:
        """
        Parse Google Maps duration text to minutes.
        
        Examples:
            "25 mins" -> 25
            "1 hour 15 mins" -> 75
            "2 hours" -> 120
        """
        mins = 0
        text = duration_text.lower()
        
        if "hour" in text:
            parts = text.split("hour")
            hours = int(parts[0].strip())
            mins += hours * 60
            
            if len(parts) > 1:
                rest = parts[1].replace("s", "").strip()
                if "min" in rest:
                    mins += int(rest.replace("min", "").strip())
        elif "min" in text:
            mins = int(text.replace("mins", "").replace("min", "").strip())
        
        return mins

    @staticmethod
    def _fallback_link(origin: str, destination: str, mode: str) -> str:
        """Generate Google Maps link without API (for fallback)."""
        from urllib.parse import quote_plus
        return (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={quote_plus(origin)}"
            f"&destination={quote_plus(destination)}"
            f"&travelmode={mode}"
        )
