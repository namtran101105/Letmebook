"""
Unified booking service that orchestrates accommodation and transportation bookings
based on user preferences.
"""
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from clients.airbnb_client import AirbnbClient
from clients.flight_client import FlightClient
from clients.busbud_client import BusbudClient
from models.trip_preferences import TripPreferences


class BookingService:
    """Service for orchestrating travel bookings based on trip preferences."""

    def __init__(self):
        """Initialize booking clients."""
        self.airbnb_client = AirbnbClient()
        self.flight_client = FlightClient()
        self.busbud_client = BusbudClient()

    def book_trip(self, preferences: TripPreferences) -> Dict[str, Any]:
        """
        Orchestrate all bookings based on user's booking preferences.

        Args:
            preferences: TripPreferences with booking_type specified

        Returns:
            Dictionary with booking results and links
        """
        results = {
            "booking_type": preferences.booking_type,
            "accommodation": None,
            "transportation": None,
            "skipped": False
        }

        # Check booking type
        if not preferences.booking_type or preferences.booking_type == "none":
            results["skipped"] = True
            results["message"] = "User opted out of booking assistance"
            print("⏭️  Skipping bookings - user chose 'none'")
            return results

        # Book accommodation if requested
        if preferences.booking_type in ["accommodation", "both"]:
            results["accommodation"] = self._book_accommodation(preferences)

        # Book transportation if requested
        if preferences.booking_type in ["transportation", "both"]:
            results["transportation"] = self._book_transportation(preferences)

        return results

    def _book_accommodation(self, preferences: TripPreferences) -> Dict[str, Any]:
        """
        Book accommodation (Airbnb) based on preferences.

        Args:
            preferences: Trip preferences with destination and dates

        Returns:
            Airbnb booking results
        """
        print(f"\n🏠 Booking accommodation via Airbnb...")

        # Build destination string
        destination = f"{preferences.city}"
        if preferences.country:
            destination += f", {preferences.country}"

        # Determine dates
        checkin = preferences.start_date
        checkout = preferences.end_date

        # Parse dates if in YYYY-MM-DD format
        if checkin and len(checkin) == 10:  # YYYY-MM-DD
            checkin_date = checkin
        else:
            checkin_date = None
            print(f"⚠️  Warning: Start date '{checkin}' is not in YYYY-MM-DD format")

        if checkout and len(checkout) == 10:  # YYYY-MM-DD
            checkout_date = checkout
        else:
            checkout_date = None
            print(f"⚠️  Warning: End date '{checkout}' is not in YYYY-MM-DD format")

        if not checkin_date or not checkout_date:
            return {
                "error": "Specific dates required for Airbnb booking",
                "destination": destination,
                "checkin": checkin,
                "checkout": checkout
            }

        # Search Airbnb
        result = self.airbnb_client.search_stays(
            destination=destination,
            checkin=checkin_date,
            checkout=checkout_date,
            adults=1  # Default to 1 adult
        )

        print(f"✅ Airbnb link generated: {result['airbnb_link']}")
        return result

    def _book_transportation(self, preferences: TripPreferences) -> Dict[str, Any]:
        """
        Book transportation (flights and buses) based on preferences.

        Args:
            preferences: Trip preferences with source, destination, and dates

        Returns:
            Transportation booking results with flight and bus options
        """
        print(f"\n✈️ Booking transportation...")

        # Check if source location is provided
        if not preferences.source_location:
            return {
                "error": "Source location required for transportation booking",
                "destination": preferences.city
            }

        origin = preferences.source_location
        destination = f"{preferences.city}"
        if preferences.country:
            destination += f", {preferences.country}"

        # Determine dates
        departure_date = preferences.start_date
        return_date = preferences.end_date

        # Parse dates if in YYYY-MM-DD format
        if departure_date and len(departure_date) == 10:
            departure = departure_date
        else:
            departure = None
            print(f"⚠️  Warning: Start date '{departure_date}' is not in YYYY-MM-DD format")

        if return_date and len(return_date) == 10:
            return_dt = return_date
        else:
            return_dt = None
            print(f"⚠️  Warning: End date '{return_date}' is not in YYYY-MM-DD format")

        if not departure or not return_dt:
            return {
                "error": "Specific dates required for transportation booking",
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date
            }

        results = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure,
            "return_date": return_dt,
            "flights": None,
            "buses": None
        }

        # Book flights
        try:
            flight_result = self.flight_client.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure,
                return_date=return_dt
            )
            results["flights"] = flight_result
            print(f"✅ Flight link: {flight_result['skyscanner_link']}")
        except Exception as e:
            print(f"❌ Flight booking failed: {e}")
            results["flights"] = {"error": str(e)}

        # Book buses/trains
        try:
            bus_result = self.busbud_client.search_all(
                origin=origin,
                destination=destination,
                departure_date=departure,
                return_date=return_dt
            )
            results["buses"] = bus_result
            print(f"✅ Bus link: {bus_result['bus_link']}")
            print(f"✅ Train link: {bus_result['train_link']}")
        except Exception as e:
            print(f"❌ Bus/train booking failed: {e}")
            results["buses"] = {"error": str(e)}

        return results

    def get_booking_summary(self, booking_results: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of booking results.

        Args:
            booking_results: Results from book_trip()

        Returns:
            Formatted summary string
        """
        booking_type = booking_results.get("booking_type")
        
        if booking_results.get("skipped"):
            return "No bookings made - user opted out of booking assistance."

        summary_parts = []
        summary_parts.append(f"Booking Type: {booking_type}")
        summary_parts.append("")

        # Accommodation summary
        if booking_results.get("accommodation"):
            accom = booking_results["accommodation"]
            if "error" not in accom:
                summary_parts.append("🏠 Accommodation (Airbnb):")
                summary_parts.append(f"   Destination: {accom['destination']}")
                summary_parts.append(f"   Check-in: {accom['checkin']}")
                summary_parts.append(f"   Check-out: {accom['checkout']}")
                summary_parts.append(f"   Link: {accom['airbnb_link']}")
                summary_parts.append("")

        # Transportation summary
        if booking_results.get("transportation"):
            trans = booking_results["transportation"]
            if "error" not in trans:
                summary_parts.append("✈️ Transportation:")
                summary_parts.append(f"   Route: {trans['origin']} → {trans['destination']}")
                summary_parts.append(f"   Depart: {trans['departure_date']}")
                summary_parts.append(f"   Return: {trans['return_date']}")
                
                if trans.get("flights") and "error" not in trans["flights"]:
                    summary_parts.append(f"   Flight: {trans['flights']['skyscanner_link']}")
                
                if trans.get("buses") and "error" not in trans["buses"]:
                    summary_parts.append(f"   Bus: {trans['buses']['bus_link']}")
                    summary_parts.append(f"   Train: {trans['buses']['train_link']}")
                
                summary_parts.append("")

        return "\n".join(summary_parts)


def main():
    """Test the booking service with sample preferences."""
    print("=" * 80)
    print("Testing Booking Service")
    print("=" * 80)

    # Test Case 1: Both accommodation and transportation
    print("\n📋 TEST CASE 1: booking_type = 'both'")
    print("-" * 80)
    
    from models.trip_preferences import TripPreferences
    
    preferences1 = TripPreferences(
        city="Toronto",
        country="Canada",
        start_date="2026-06-15",
        end_date="2026-06-20",
        budget=2000.0,
        interests=["Food and Beverage"],
        pace="relaxed",
        location_preference="downtown",
        booking_type="both",
        source_location="Montreal"
    )
    
    service = BookingService()
    results1 = service.book_trip(preferences1)
    print("\n" + service.get_booking_summary(results1))

    # Test Case 2: Accommodation only
    print("\n📋 TEST CASE 2: booking_type = 'accommodation'")
    print("-" * 80)
    
    preferences2 = TripPreferences(
        city="Toronto",
        country="Canada",
        start_date="2026-06-15",
        end_date="2026-06-20",
        budget=1000.0,
        interests=["Culture and History"],
        pace="moderate",
        booking_type="accommodation",
        source_location=None  # Not needed for accommodation only
    )
    
    results2 = service.book_trip(preferences2)
    print("\n" + service.get_booking_summary(results2))

    # Test Case 3: Transportation only
    print("\n📋 TEST CASE 3: booking_type = 'transportation'")
    print("-" * 80)
    
    preferences3 = TripPreferences(
        city="Toronto",
        country="Canada",
        start_date="2026-06-15",
        end_date="2026-06-20",
        budget=500.0,
        interests=["Sport"],
        pace="packed",
        booking_type="transportation",
        source_location="Ottawa"
    )
    
    results3 = service.book_trip(preferences3)
    print("\n" + service.get_booking_summary(results3))

    # Test Case 4: No booking
    print("\n📋 TEST CASE 4: booking_type = 'none'")
    print("-" * 80)
    
    preferences4 = TripPreferences(
        city="Toronto",
        country="Canada",
        start_date="2026-06-15",
        end_date="2026-06-20",
        budget=1500.0,
        interests=["Entertainment"],
        pace="relaxed",
        booking_type="none",
        source_location=None
    )
    
    results4 = service.book_trip(preferences4)
    print("\n" + service.get_booking_summary(results4))

    print("\n" + "=" * 80)
    print("✅ All test cases completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
