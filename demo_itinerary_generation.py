#!/usr/bin/env python3
"""
Demo script for Itinerary Generation Service.
Shows how to generate day-by-day itineraries from trip preferences.
"""
import sys
import json
import asyncio

sys.path.insert(0, 'backend')

from services.itinerary_service import ItineraryService


async def main():
    print("=" * 70)
    print("  ITINERARY GENERATION SERVICE - DEMO")
    print("=" * 70)

    # Initialize service
    print("\n[1] Initializing Itinerary Generation Service...")
    service = ItineraryService()
    print("✅ Service initialized (uses Gemini API)")

    # Example 1: 3-day moderate trip
    print("\n" + "=" * 70)
    print("EXAMPLE 1: 3-Day Moderate Pace Trip")
    print("=" * 70)

    preferences_1 = {
        "city": "Kingston",
        "country": "Canada",
        "start_date": "2026-05-10",
        "end_date": "2026-05-12",
        "duration_days": 3,
        "budget": 900.0,
        "budget_currency": "CAD",
        "interests": ["museums", "food", "waterfront"],
        "pace": "moderate",
        "location_preference": "downtown"
    }

    print("\nInput Preferences:")
    print(json.dumps(preferences_1, indent=2))

    print("\n[Generating itinerary... this may take 30-60 seconds]")

    try:
        itinerary_1 = await service.generate_itinerary(
            preferences=preferences_1,
            request_id="demo-001"
        )

        print(f"\n✅ Itinerary Generated!")
        print(f"   Trip ID: {itinerary_1.trip_id}")
        print(f"   Days: {len(itinerary_1.days)}")
        print(f"   Total Activities: {itinerary_1.total_activities}")
        print(f"   Avg Activities/Day: {itinerary_1.activities_per_day_avg:.1f}")
        print(f"   Total Cost: ${itinerary_1.total_spent:.2f} / ${itinerary_1.total_budget:.2f}")
        print(f"   Total Travel Time: {itinerary_1.total_travel_time_hours:.1f} hours")

        # Display Day 1 details
        print(f"\n📅 Day 1 - {itinerary_1.days[0].date}")
        print(f"   Budget: ${itinerary_1.days[0].daily_budget_spent:.2f} / ${itinerary_1.days[0].daily_budget_allocated:.2f}")

        print(f"\n   Morning Departure:")
        dep = itinerary_1.days[0].morning_departure
        if dep:
            print(f"   └─ From: {dep.from_location}")
            print(f"   └─ To: {dep.to_location}")
            print(f"   └─ Travel: {dep.duration_minutes} min by {dep.mode}")

        print(f"\n   Activities:")
        for activity in itinerary_1.days[0].activities:
            print(f"   • {activity.planned_start}-{activity.planned_end}: {activity.venue_name}")
            print(f"     └─ Category: {activity.category} | Cost: ${activity.estimated_cost}")
            print(f"     └─ {activity.notes}")

        print(f"\n   Meals:")
        for meal in itinerary_1.days[0].meals:
            print(f"   • {meal.planned_time}: {meal.meal_type.title()} at {meal.venue_name} (${meal.estimated_cost})")

        print(f"\n   Evening Return:")
        ret = itinerary_1.days[0].evening_return
        if ret:
            print(f"   └─ From: {ret.from_location}")
            print(f"   └─ To: {ret.to_location}")
            print(f"   └─ Travel: {ret.duration_minutes} min by {ret.mode}")

        # Save to file
        output_file = f"itinerary_{itinerary_1.trip_id}.json"
        with open(output_file, 'w') as f:
            json.dump(itinerary_1.to_dict(), f, indent=2)

        print(f"\n💾 Full itinerary saved to: {output_file}")

    except Exception as e:
        print(f"\n❌ Error generating itinerary: {e}")
        import traceback
        traceback.print_exc()

    # Example 2: 5-day relaxed trip
    print("\n" + "=" * 70)
    print("EXAMPLE 2: 5-Day Relaxed Pace Trip")
    print("=" * 70)

    preferences_2 = {
        "city": "Kingston",
        "country": "Canada",
        "start_date": "2026-06-01",
        "end_date": "2026-06-05",
        "duration_days": 5,
        "budget": 1500.0,
        "budget_currency": "CAD",
        "interests": ["history", "arts", "nature"],
        "pace": "relaxed",
        "location_preference": "near waterfront"
    }

    print("\nInput Preferences:")
    print(json.dumps(preferences_2, indent=2))

    print("\n[Generating itinerary... this may take 30-60 seconds]")

    try:
        itinerary_2 = await service.generate_itinerary(
            preferences=preferences_2,
            request_id="demo-002"
        )

        print(f"\n✅ Itinerary Generated!")
        print(f"   Trip ID: {itinerary_2.trip_id}")
        print(f"   Days: {len(itinerary_2.days)}")
        print(f"   Total Activities: {itinerary_2.total_activities}")
        print(f"   Avg Activities/Day: {itinerary_2.activities_per_day_avg:.1f}")
        print(f"   Total Cost: ${itinerary_2.total_spent:.2f} / ${itinerary_2.total_budget:.2f}")

        # Display summary of all days
        print(f"\n📅 Daily Summary:")
        for day in itinerary_2.days:
            print(f"\n   Day {day.day_number} - {day.date}")
            print(f"   └─ {day.total_activities} activities, ${day.daily_budget_spent:.2f} spent")
            for activity in day.activities:
                print(f"      • {activity.planned_start}: {activity.venue_name}")

        # Save to file
        output_file = f"itinerary_{itinerary_2.trip_id}.json"
        with open(output_file, 'w') as f:
            json.dump(itinerary_2.to_dict(), f, indent=2)

        print(f"\n💾 Full itinerary saved to: {output_file}")

    except Exception as e:
        print(f"\n❌ Error generating itinerary: {e}")

    print("\n" + "=" * 70)
    print("  DEMO COMPLETE!")
    print("=" * 70)
    print("\n💡 Tips:")
    print("  - Itinerary service uses Gemini API")
    print("  - Generation takes 30-60 seconds per itinerary")
    print("  - Budget minimum: $50/day (for meals + activities)")
    print("  - Pace options: relaxed (2-3 activities/day), moderate (4-5), packed (6-8)")
    print("  - Check generated JSON files for full details")


if __name__ == "__main__":
    asyncio.run(main())
