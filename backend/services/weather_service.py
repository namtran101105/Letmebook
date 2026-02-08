"""
Weather service that fetches weather forecasts for trip dates.
"""
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from clients.weather_client import WeatherClient
from models.trip_preferences import TripPreferences


class WeatherService:
    """Service for fetching weather forecasts based on trip preferences."""

    def __init__(self):
        """Initialize weather client."""
        self.weather_client = WeatherClient()

    def get_trip_weather(self, preferences: TripPreferences) -> Dict[str, Any]:
        """
        Get weather forecast for the entire trip duration.

        Args:
            preferences: TripPreferences with destination and dates

        Returns:
            Dictionary with weather forecast for each day
        """
        result = {
            "city": preferences.city,
            "country": preferences.country,
            "start_date": preferences.start_date,
            "end_date": preferences.end_date,
            "duration_days": None,
            "forecasts": [],
            "error": None
        }

        # Build city string
        city = f"{preferences.city}"
        if preferences.country:
            city += f", {preferences.country}"

        # Check if dates are in proper format
        if not preferences.start_date or not preferences.end_date:
            result["error"] = "Start date and end date are required"
            return result

        # Only handle YYYY-MM-DD format
        if len(preferences.start_date) != 10 or len(preferences.end_date) != 10:
            result["error"] = f"Dates must be in YYYY-MM-DD format. Got: {preferences.start_date} to {preferences.end_date}"
            return result

        # Generate date range
        dates = self._generate_date_range(preferences.start_date, preferences.end_date)
        
        if not dates:
            result["error"] = f"Could not generate date range from {preferences.start_date} to {preferences.end_date}"
            return result

        result["duration_days"] = len(dates)

        print(f"\n🌤️  Fetching weather for {city}...")
        print(f"   Dates: {preferences.start_date} to {preferences.end_date} ({len(dates)} days)")

        # Fetch weather
        try:
            weather_result = self.weather_client.get_weather(city, dates)
            result["city"] = weather_result.get("city", preferences.city)
            result["country"] = weather_result.get("country", preferences.country)
            result["timezone"] = weather_result.get("timezone")
            result["forecasts"] = weather_result.get("forecasts", [])
            
            print(f"✅ Weather forecast retrieved: {len(result['forecasts'])} days")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Failed to fetch weather: {e}")

        return result

    def _generate_date_range(self, start_date: str, end_date: str) -> List[str]:
        """
        Generate a list of dates between start_date and end_date (inclusive).
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            List of date strings in YYYY-MM-DD format
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            dates = []
            current = start
            while current <= end:
                dates.append(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)
            
            return dates
        except ValueError:
            return []

    def get_weather_summary(self, weather_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of weather forecast.

        Args:
            weather_result: Results from get_trip_weather()

        Returns:
            Formatted summary string
        """
        if weather_result.get("error"):
            return f"❌ Error: {weather_result['error']}"

        summary_parts = []
        summary_parts.append("🌤️  Weather Forecast")
        summary_parts.append("=" * 80)
        summary_parts.append(f"Location: {weather_result['city']}, {weather_result['country']}")
        summary_parts.append(f"Dates: {weather_result['start_date']} to {weather_result['end_date']}")
        summary_parts.append(f"Duration: {weather_result['duration_days']} day(s)")
        if weather_result.get("timezone"):
            summary_parts.append(f"Timezone: {weather_result['timezone']}")
        summary_parts.append("=" * 80)
        summary_parts.append("")

        forecasts = weather_result.get("forecasts", [])
        if not forecasts:
            summary_parts.append("No forecast data available")
            return "\n".join(summary_parts)

        summary_parts.append("Daily Forecast:")
        summary_parts.append("-" * 80)

        for f in forecasts:
            summary_parts.append(f"\n📅 {f['date']}  |  {f['condition']}")
            summary_parts.append(f"   🌡️  Temperature: {f['temp_min_c']}°C - {f['temp_max_c']}°C")
            summary_parts.append(f"   🌧️  Rain: {f['precipitation_mm']}mm ({f['precipitation_chance']}% chance)")
            summary_parts.append(f"   💨 Wind: {f['wind_speed_kmh']} km/h")
            summary_parts.append(f"   ☀️  Sun: {f['sunrise']} - {f['sunset']}")

        summary_parts.append("\n" + "=" * 80)
        
        return "\n".join(summary_parts)

    def get_weather_conditions_summary(self, weather_result: Dict[str, Any]) -> str:
        """
        Generate a brief weather conditions summary (useful for trip planning).

        Args:
            weather_result: Results from get_trip_weather()

        Returns:
            Brief summary of weather conditions
        """
        if weather_result.get("error"):
            return f"Weather unavailable: {weather_result['error']}"

        forecasts = weather_result.get("forecasts", [])
        if not forecasts:
            return "No weather data available"

        # Analyze conditions
        total_days = len(forecasts)
        rainy_days = sum(1 for f in forecasts if f['precipitation_chance'] > 50)
        avg_temp = sum(f['temp_max_c'] for f in forecasts) / total_days
        
        conditions = []
        if avg_temp < 10:
            conditions.append("cold")
        elif avg_temp > 25:
            conditions.append("warm")
        else:
            conditions.append("mild")
        
        if rainy_days > total_days / 2:
            conditions.append("rainy")
        elif rainy_days > 0:
            conditions.append("some rain expected")
        else:
            conditions.append("mostly dry")

        return f"{', '.join(conditions).capitalize()} ({avg_temp:.1f}°C avg, {rainy_days}/{total_days} rainy days)"


def main():
    """Test the weather service with sample preferences."""
    print("=" * 80)
    print("Testing Weather Service")
    print("=" * 80)

    from models.trip_preferences import TripPreferences
    
    # Test Case 1: Valid trip with specific dates
    print("\n📋 TEST CASE 1: Toronto trip with specific dates")
    print("-" * 80)
    
    preferences1 = TripPreferences(
        city="Toronto",
        country="Canada",
        start_date="2026-06-15",
        end_date="2026-06-20",
        budget=2000.0,
        interests=["Food and Beverage"],
        pace="relaxed"
    )
    
    service = WeatherService()
    result1 = service.get_trip_weather(preferences1)
    print("\n" + service.get_weather_summary(result1))
    print("\n📊 Quick Summary:", service.get_weather_conditions_summary(result1))

    # Test Case 2: Trip with invalid dates
    print("\n\n📋 TEST CASE 2: Trip with season-based dates (will fail)")
    print("-" * 80)
    
    preferences2 = TripPreferences(
        city="Toronto",
        country="Canada",
        start_date="summer 2026",
        end_date=None,
        budget=1500.0,
        interests=["Culture and History"],
        pace="moderate"
    )
    
    result2 = service.get_trip_weather(preferences2)
    print(f"\n❌ Error: {result2['error']}")

    # Test Case 3: Short trip
    print("\n\n📋 TEST CASE 3: Weekend trip to Montreal")
    print("-" * 80)
    
    preferences3 = TripPreferences(
        city="Montreal",
        country="Canada",
        start_date="2026-02-14",
        end_date="2026-02-16",
        budget=500.0,
        interests=["Entertainment"],
        pace="packed"
    )
    
    result3 = service.get_trip_weather(preferences3)
    print("\n" + service.get_weather_summary(result3))
    print("\n📊 Quick Summary:", service.get_weather_conditions_summary(result3))

    print("\n" + "=" * 80)
    print("✅ All test cases completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
