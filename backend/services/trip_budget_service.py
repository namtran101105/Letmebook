"""
Budget service that estimates trip costs from trip preferences.
Uses real Airbnb prices and flight estimates to check budget feasibility.
"""
import sys
import os
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.budget_estimator import BudgetEstimator
from models.trip_preferences import TripPreferences


class TripBudgetService:
    """Service for estimating trip budgets based on trip preferences."""

    def __init__(self):
        """Initialize budget estimator."""
        self.budget_estimator = BudgetEstimator()

    def estimate_trip_budget(self, preferences: TripPreferences) -> Dict[str, Any]:
        """
        Estimate trip budget from preferences.

        Args:
            preferences: TripPreferences with destination, dates, budget

        Returns:
            Dictionary with cost breakdown, budget status, and booking links
        """
        result = {
            "preferences": {
                "city": preferences.city,
                "country": preferences.country,
                "start_date": preferences.start_date,
                "end_date": preferences.end_date,
                "budget": preferences.budget,
                "booking_type": preferences.booking_type,
                "source_location": preferences.source_location,
            },
            "estimation": None,
            "error": None
        }

        # Validate required fields
        if not preferences.city:
            result["error"] = "Destination city is required"
            return result

        if not preferences.budget:
            result["error"] = "Budget is required"
            return result

        # Check dates format
        if not preferences.start_date or len(preferences.start_date) != 10:
            result["error"] = f"Start date must be in YYYY-MM-DD format. Got: {preferences.start_date}"
            return result

        if not preferences.end_date or len(preferences.end_date) != 10:
            result["error"] = f"End date must be in YYYY-MM-DD format. Got: {preferences.end_date}"
            return result

        # Build destination
        destination = f"{preferences.city}"
        if preferences.country:
            destination += f", {preferences.country}"

        # Check booking type
        booking_type = preferences.booking_type or "both"
        
        # Determine if we need transportation costs
        if booking_type in ["transportation", "both"]:
            # Need origin for flights
            if not preferences.source_location:
                result["error"] = "Source location required for transportation booking"
                return result
            
            origin = preferences.source_location
        else:
            # Accommodation only - use same city as origin (zero flight cost)
            origin = preferences.city

        print(f"\n💰 Estimating budget for {destination}...")
        print(f"   Origin: {origin}")
        print(f"   Dates: {preferences.start_date} to {preferences.end_date}")
        print(f"   Budget: ${preferences.budget} {preferences.budget_currency}")
        print(f"   Booking type: {booking_type}")

        # Estimate budget
        try:
            estimation = self.budget_estimator.estimate(
                origin=origin,
                destination=destination,
                departure_date=preferences.start_date,
                return_date=preferences.end_date,
                budget=preferences.budget,
                adults=1  # Default to 1 adult
            )
            
            result["estimation"] = estimation
            
            status = "✅ WITHIN BUDGET" if estimation["within_budget"] else "⚠️ OVER BUDGET"
            print(f"   Status: {status}")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Failed to estimate budget: {e}")

        return result

    def get_budget_summary(self, budget_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of budget estimation.

        Args:
            budget_result: Results from estimate_trip_budget()

        Returns:
            Formatted summary string
        """
        if budget_result.get("error"):
            return f"❌ Error: {budget_result['error']}"

        prefs = budget_result["preferences"]
        est = budget_result["estimation"]

        summary_parts = []
        summary_parts.append("💰 Budget Estimation")
        summary_parts.append("=" * 80)
        summary_parts.append(f"Destination: {prefs['city']}, {prefs['country']}")
        if prefs['source_location']:
            summary_parts.append(f"Origin: {prefs['source_location']}")
        summary_parts.append(f"Dates: {prefs['start_date']} to {prefs['end_date']}")
        summary_parts.append(f"Your Budget: ${est['budget']:.0f} CAD")
        summary_parts.append(f"Duration: {est['nights']} night(s)")
        
        status = "✅ WITHIN BUDGET" if est["within_budget"] else "⚠️ OVER BUDGET"
        summary_parts.append(f"Status: {status}")
        summary_parts.append("=" * 80)
        summary_parts.append("")

        # Airbnb prices
        ap = est["prices"]["airbnb_per_night"]
        summary_parts.append(f"🏠 Accommodation ({ap['source']}, {ap['listings_found']} listings)")
        if ap["low"]:
            summary_parts.append(f"   Lowest:  ${ap['low']:.2f}/night")
            summary_parts.append(f"   Highest: ${ap['high']:.2f}/night")
            summary_parts.append(f"   Average: ${ap['average']:.2f}/night")
        else:
            summary_parts.append("   No prices available")
        summary_parts.append("")

        # Flight prices
        fp = est["prices"]["flight_per_person"]
        summary_parts.append(f"✈️  Flights ({fp['source']})")
        summary_parts.append(f"   Low:  ${fp['low']}/person round-trip")
        summary_parts.append(f"   High: ${fp['high']}/person round-trip")
        summary_parts.append("")

        # Totals
        cheap = est["cheapest_total"]
        avg = est["average_total"]
        exp = est["most_expensive_total"]
        summary_parts.append("📊 Total Cost Scenarios:")
        summary_parts.append(f"   Cheapest:        ${cheap['total']:.0f}  "
              f"(flights ${cheap['flights']:.0f} + stay ${cheap['accommodation']:.0f})")
        summary_parts.append(f"   Average:         ${avg['total']:.0f}  "
              f"(flights ${avg['flights']:.0f} + stay ${avg['accommodation']:.0f})")
        summary_parts.append(f"   Most expensive:  ${exp['total']:.0f}  "
              f"(flights ${exp['flights']:.0f} + stay ${exp['accommodation']:.0f})")
        summary_parts.append("")

        summary_parts.append("💵 Budget Remaining:")
        summary_parts.append(f"   At cheapest: ${est['remaining_at_cheapest']:.0f}")
        summary_parts.append(f"   At average:  ${est['remaining_at_average']:.0f}")
        summary_parts.append("")

        summary_parts.append("🔗 Booking Links:")
        summary_parts.append(f"   Flights (Skyscanner): {est['links']['skyscanner']}")
        if est['links']['busbud_bus']:
            summary_parts.append(f"   Bus:   {est['links']['busbud_bus']}")
            summary_parts.append(f"   Train: {est['links']['busbud_train']}")
        summary_parts.append(f"   Accommodation (Airbnb): {est['links']['airbnb']}")
        summary_parts.append("")

        summary_parts.append("=" * 80)
        
        return "\n".join(summary_parts)

    def get_budget_status_summary(self, budget_result: Dict[str, Any]) -> str:
        """
        Generate a brief budget status summary.

        Args:
            budget_result: Results from estimate_trip_budget()

        Returns:
            Brief summary of budget status
        """
        if budget_result.get("error"):
            return f"Budget unavailable: {budget_result['error']}"

        est = budget_result["estimation"]
        
        if est["within_budget"]:
            remaining = est["remaining_at_average"]
            return f"✅ Within budget! ${remaining:.0f} remaining at average prices."
        else:
            shortage = abs(est["remaining_at_cheapest"])
            return f"⚠️ Over budget by ${shortage:.0f} even at cheapest prices."


def main():
    """Test the budget service with sample preferences."""
    print("=" * 80)
    print("Testing Trip Budget Service")
    print("=" * 80)

    from models.trip_preferences import TripPreferences
    
    # Test Case 1: Both accommodation and transportation
    print("\n📋 TEST CASE 1: Toronto trip from Montreal (booking_type='both')")
    print("-" * 80)
    
    preferences1 = TripPreferences(
        city="Toronto",
        country="Canada",
        start_date="2026-06-15",
        end_date="2026-06-20",
        budget=2000.0,
        interests=["Food and Beverage"],
        pace="relaxed",
        booking_type="both",
        source_location="Montreal"
    )
    
    service = TripBudgetService()
    result1 = service.estimate_trip_budget(preferences1)
    print("\n" + service.get_budget_summary(result1))
    print(f"Quick Status: {service.get_budget_status_summary(result1)}")

    # Test Case 2: Accommodation only
    print("\n\n📋 TEST CASE 2: Toronto trip (booking_type='accommodation')")
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
        source_location=None  # Not needed
    )
    
    result2 = service.estimate_trip_budget(preferences2)
    print("\n" + service.get_budget_summary(result2))
    print(f"Quick Status: {service.get_budget_status_summary(result2)}")

    # Test Case 3: Invalid dates
    print("\n\n📋 TEST CASE 3: Trip with invalid dates (will fail)")
    print("-" * 80)
    
    preferences3 = TripPreferences(
        city="Toronto",
        country="Canada",
        start_date="summer 2026",
        end_date=None,
        budget=1500.0,
        interests=["Entertainment"],
        pace="packed",
        booking_type="both",
        source_location="Montreal"
    )
    
    result3 = service.estimate_trip_budget(preferences3)
    print(f"\n❌ Error: {result3['error']}")

    print("\n" + "=" * 80)
    print("✅ All test cases completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
