"""
Client for Open-Meteo Weather API.
Fetches weather forecasts for a city on specific dates.
No API key required.
"""

from typing import Dict, Any, List

import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes -> human-readable descriptions
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherClient:
    """Client for fetching weather forecasts via Open-Meteo (free, no key)."""

    def get_weather(
        self,
        city: str,
        dates: List[str],
    ) -> Dict[str, Any]:
        """
        Get weather forecast for a city on specific dates.

        Args:
            city: City name (e.g. "Kingston, Ontario").
            dates: List of dates in YYYY-MM-DD format.

        Returns:
            Dict with city info and a list of daily forecasts.
        """
        if not dates:
            raise ValueError("Need at least one date")

        # Step 1: Geocode the city name to coordinates
        coords = self._geocode(city)

        # Step 2: Fetch weather for the date range
        start_date = min(dates)
        end_date = max(dates)

        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "daily": ",".join([
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "sunrise",
                "sunset",
            ]),
            "timezone": "auto",
            "start_date": start_date,
            "end_date": end_date,
        }

        resp = httpx.get(FORECAST_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Step 3: Parse and filter to only the requested dates
        daily = data["daily"]
        all_dates_from_api = daily["time"]

        requested = set(dates)
        forecasts = []

        for i, date in enumerate(all_dates_from_api):
            if date not in requested:
                continue

            code = daily["weather_code"][i]
            forecasts.append({
                "date": date,
                "condition": WEATHER_CODES.get(code, f"Unknown ({code})"),
                "weather_code": code,
                "temp_max_c": daily["temperature_2m_max"][i],
                "temp_min_c": daily["temperature_2m_min"][i],
                "precipitation_mm": daily["precipitation_sum"][i],
                "precipitation_chance": daily["precipitation_probability_max"][i],
                "wind_speed_kmh": daily["wind_speed_10m_max"][i],
                "sunrise": daily["sunrise"][i],
                "sunset": daily["sunset"][i],
            })

        return {
            "city": coords["name"],
            "country": coords["country"],
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "timezone": data.get("timezone", ""),
            "forecasts": forecasts,
        }

    def _geocode(self, city: str) -> Dict[str, Any]:
        """Convert a city name to coordinates using Open-Meteo geocoding.

        Handles inputs like "Kingston", "Kingston, Ontario", or
        "Kingston, Ontario, Canada" by searching for the city name
        and matching against any extra qualifiers (region, country).
        """
        # Split "Kingston, Ontario" into name="Kingston", qualifiers=["ontario"]
        parts = [p.strip() for p in city.split(",")]
        search_name = parts[0]
        qualifiers = [q.lower() for q in parts[1:] if q]

        resp = httpx.get(
            GEOCODING_URL,
            params={"name": search_name, "count": 10},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results")
        if not results:
            raise ValueError(f"City not found: {city}")

        # If qualifiers given, try to find a matching result
        if qualifiers:
            for r in results:
                fields = " ".join([
                    r.get("admin1", ""),
                    r.get("admin2", ""),
                    r.get("country", ""),
                ]).lower()
                if all(q in fields for q in qualifiers):
                    return {
                        "name": r["name"],
                        "country": r.get("country", ""),
                        "latitude": r["latitude"],
                        "longitude": r["longitude"],
                    }

        # Fallback to first result
        r = results[0]
        return {
            "name": r["name"],
            "country": r.get("country", ""),
            "latitude": r["latitude"],
            "longitude": r["longitude"],
        }
