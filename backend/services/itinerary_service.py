"""
Itinerary timetable generator service.

Accepts validated trip preferences (JSON dict), calls Google Gemini to
produce a day-by-day timetable, parses the result into an Itinerary
dataclass, and validates feasibility before returning.

Usage:
    from backend.services.itinerary_service import ItineraryService

    service = ItineraryService()
    itinerary = await service.generate_itinerary(preferences, request_id="req-001")
    print(itinerary.to_dict())
"""

import json
import logging
import asyncio
from datetime import datetime, date
from typing import Dict, Any, List, Optional

from backend.clients.gemini_client import GeminiClient, ExternalAPIError
from backend.models.itinerary import (
    Itinerary,
    ItineraryDay,
    Activity,
    Meal,
    TravelSegment,
)
from backend.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini system prompt for itinerary timetable generation
# ---------------------------------------------------------------------------

GEMINI_ITINERARY_SYSTEM_INSTRUCTION = """\
You are an expert Kingston, Ontario trip planner that generates precise,
feasible day-by-day itinerary timetables.

## Your Objectives
1. Create a coherent daily schedule that aligns with the traveller's
   interests, pace preference, and budget.
2. Ensure practical geography — activities should follow efficient routing
   from the starting area, minimising backtracking.
3. Include realistic time slots with no overlapping events.

## Hard Constraints (MUST follow)
- Every activity must have explicit start and end times (HH:MM, 24-hour).
- No two events may overlap within the same day.
- Each day MUST include at least a lunch AND a dinner meal entry.
- Activity durations and buffer times MUST match the pace:
  * Relaxed  — 2-3 activities/day, 90-120 min each, 20 min buffers,
               90 min lunch, 120 min dinner.
  * Moderate — 4-5 activities/day, 60-90 min each, 15 min buffers,
               60 min lunch, 90 min dinner.
  * Packed   — 6-8 activities/day, 30-60 min each, 5 min buffers,
               45 min lunch, 60 min dinner.
- The estimated daily cost (activities + meals) MUST NOT exceed the
  daily budget.
- First activity each day should be near the starting location; last
  activity should allow an easy return.
- Budget minimum: $50 CAD per day for meals + activities.

## Quality Checks (perform before responding)
1. Verify total number of days matches the requested duration.
2. Verify every day has at least one activity AND two meals.
3. Verify daily costs sum to the per-day total shown.
4. Verify the user's interests are represented across the trip.
5. Verify times are in chronological order with no overlaps.

## Output Format
Return ONLY a valid JSON object (no markdown fences, no prose).
The schema is:
{
  "itinerary": {
    "option_name": "<string>",
    "total_cost": <number>,
    "activities_per_day_avg": <number>,
    "total_travel_time_hours": <number>,
    "days": [
      {
        "day": <int>,
        "date": "YYYY-MM-DD",
        "morning_departure": {
          "time": "HH:MM",
          "from": "<starting_location>",
          "to": "<first_venue>",
          "travel_minutes": <int>,
          "mode": "<transport_mode>"
        },
        "activities": [
          {
            "time_start": "HH:MM",
            "time_end": "HH:MM",
            "venue_name": "<string>",
            "category": "<interest_category>",
            "cost": <number>,
            "duration_reason": "<why this duration for this pace>",
            "notes": "<brief description>"
          }
        ],
        "meals": [
          {
            "meal_type": "lunch|dinner",
            "venue_name": "<string>",
            "time": "HH:MM",
            "cost": <number>
          }
        ],
        "evening_return": {
          "time": "HH:MM",
          "from": "<last_venue>",
          "to": "<starting_location>",
          "travel_minutes": <int>,
          "mode": "<transport_mode>"
        },
        "daily_budget_allocated": <number>,
        "daily_budget_spent": <number>
      }
    ]
  }
}

## Example (minimal, 1-day moderate pace)
Input: Kingston, 2026-05-10, 1 day, $357/day budget, interests: museums, food
Output:
{
  "itinerary": {
    "option_name": "Moderate-Paced Kingston Explorer",
    "total_cost": 195.0,
    "activities_per_day_avg": 4,
    "total_travel_time_hours": 0.8,
    "days": [
      {
        "day": 1,
        "date": "2026-05-10",
        "morning_departure": {
          "time": "08:45",
          "from": "Downtown Kingston",
          "to": "Fort Henry",
          "travel_minutes": 15,
          "mode": "mixed"
        },
        "activities": [
          {
            "time_start": "09:00",
            "time_end": "10:15",
            "venue_name": "Fort Henry National Historic Site",
            "category": "museums",
            "cost": 22.0,
            "duration_reason": "Moderate pace — standard guided tour",
            "notes": "19th-century British military fortification"
          },
          {
            "time_start": "10:30",
            "time_end": "11:45",
            "venue_name": "Royal Military College Museum",
            "category": "museums",
            "cost": 0.0,
            "duration_reason": "Moderate pace — free museum visit",
            "notes": "Military artifacts and history exhibits"
          },
          {
            "time_start": "13:15",
            "time_end": "14:30",
            "venue_name": "Kingston City Hall",
            "category": "museums",
            "cost": 0.0,
            "duration_reason": "Moderate pace — self-guided tour",
            "notes": "National Historic Site with stunning architecture"
          },
          {
            "time_start": "14:45",
            "time_end": "16:00",
            "venue_name": "Kingston Waterfront Trail",
            "category": "food",
            "cost": 0.0,
            "duration_reason": "Moderate pace — leisurely walk along Lake Ontario",
            "notes": "Scenic waterfront walk from City Park to Breakwater Park"
          }
        ],
        "meals": [
          {
            "meal_type": "lunch",
            "venue_name": "Dianne's Fish Shack & Smokehouse",
            "time": "12:00",
            "cost": 28.0
          },
          {
            "meal_type": "dinner",
            "venue_name": "Chez Piggy",
            "time": "18:00",
            "cost": 45.0
          }
        ],
        "evening_return": {
          "time": "19:30",
          "from": "Chez Piggy",
          "to": "Downtown Kingston",
          "travel_minutes": 5,
          "mode": "walking"
        },
        "daily_budget_allocated": 357.0,
        "daily_budget_spent": 95.0
      }
    ]
  }
}
"""


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class ItineraryGenerationError(Exception):
    """Raised when itinerary generation fails feasibility checks."""

    def __init__(self, reason: str, constraints: dict):
        self.reason = reason
        self.constraints = constraints
        super().__init__(f"Itinerary generation failed: {reason}")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ItineraryService:
    """Generates day-by-day itinerary timetables via Gemini."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        """
        Args:
            gemini_client: Injected client (useful for testing).
                           Created automatically if omitted.
        """
        self.gemini_client = gemini_client or GeminiClient()
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_itinerary(
        self,
        preferences: Dict[str, Any],
        request_id: str,
    ) -> Itinerary:
        """
        Generate a complete itinerary from trip preferences.

        Args:
            preferences: Dict matching the required input schema (10 required fields).
            request_id: UUID for log correlation.

        Returns:
            Populated Itinerary dataclass.

        Raises:
            ValueError: If preferences fail validation.
            ExternalAPIError: If Gemini API call fails.
            ItineraryGenerationError: If the generated plan fails feasibility.
        """
        self.logger.info(
            "Starting itinerary generation",
            extra={
                "request_id": request_id,
                "dates": f"{preferences.get('start_date')} → {preferences.get('end_date')}",
                "pace": preferences.get("pace"),
                "budget": preferences.get("budget"),
            },
        )

        # 1. Validate & normalise
        validated = self._validate_preferences(preferences, request_id)

        # 2. Build prompt
        prompt = self._build_generation_prompt(validated)

        # 3. Call Gemini
        try:
            response_text = await self.gemini_client.generate_content(
                prompt=prompt,
                system_instruction=GEMINI_ITINERARY_SYSTEM_INSTRUCTION,
                temperature=settings.GEMINI_ITINERARY_TEMPERATURE,
                max_tokens=settings.GEMINI_ITINERARY_MAX_TOKENS,
                request_id=request_id,
            )
        except ExternalAPIError:
            self.logger.error(
                "Gemini API failed during itinerary generation",
                extra={"request_id": request_id},
                exc_info=True,
            )
            raise

        # 4. Parse response JSON
        itinerary_data = self._parse_gemini_response(response_text, request_id)

        # 5. Map to dataclass
        itinerary = self._build_itinerary_object(itinerary_data, validated, request_id)

        # 6. Feasibility check
        check = self._validate_feasibility(itinerary, validated, request_id)
        if not check["feasible"]:
            raise ItineraryGenerationError(
                reason="Generated itinerary is not feasible",
                constraints=check,
            )

        self.logger.info(
            "Itinerary generation complete",
            extra={
                "request_id": request_id,
                "days": len(itinerary.days),
                "total_activities": itinerary.total_activities,
                "total_cost": itinerary.total_spent,
            },
        )
        return itinerary

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_preferences(
        self, prefs: Dict[str, Any], request_id: str
    ) -> Dict[str, Any]:
        """Validate the 10 required fields and normalise optional defaults."""
        v = prefs.copy()

        # --- Required field presence ---
        required = [
            "city", "country", "start_date", "end_date",
            "duration_days", "budget", "budget_currency",
            "interests", "pace", "location_preference",
        ]
        missing = [f for f in required if not v.get(f)]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # --- Dates ---
        start = date.fromisoformat(v["start_date"])
        end = date.fromisoformat(v["end_date"])
        if end <= start:
            raise ValueError("end_date must be after start_date")
        calculated = (end - start).days + 1
        if v["duration_days"] != calculated:
            self.logger.warning(
                "duration_days mismatch — using date range",
                extra={"request_id": request_id, "given": v["duration_days"], "calculated": calculated},
            )
            v["duration_days"] = calculated

        # --- Budget (NON-NEGOTIABLE) ---
        daily = v["budget"] / v["duration_days"]
        v["daily_budget"] = daily
        if daily < settings.MIN_DAILY_BUDGET:
            raise ValueError(
                f"Daily budget ${daily:.2f} is below the minimum "
                f"${settings.MIN_DAILY_BUDGET}/day for meals + activities"
            )

        # --- Pace ---
        pace = v["pace"].lower()
        if pace not in settings.VALID_PACES:
            raise ValueError(f"Invalid pace '{pace}'. Must be: relaxed, moderate, or packed")
        v["pace"] = pace

        # --- Interests ---
        if not v.get("interests"):
            raise ValueError("At least one interest is required")

        # --- Optional defaults ---
        v.setdefault("starting_location", v.get("location_preference", "Downtown Kingston"))
        v.setdefault("hours_per_day", 8)
        v.setdefault("transportation_modes", ["mixed"])
        v.setdefault("group_size", None)
        v.setdefault("group_type", None)
        v.setdefault("dietary_restrictions", [])
        v.setdefault("accessibility_needs", [])
        v.setdefault("weather_tolerance", None)
        v.setdefault("must_see_venues", [])
        v.setdefault("must_avoid_venues", [])

        return v

    # ------------------------------------------------------------------
    # Prompt builder
    # ------------------------------------------------------------------

    def _build_generation_prompt(self, prefs: Dict[str, Any]) -> str:
        """Build the per-request Gemini prompt."""
        pace = prefs["pace"]
        pp = settings.PACE_PARAMS[pace]
        min_act, max_act = pp["activities_per_day"]
        min_dur, max_dur = pp["minutes_per_activity"]

        pace_block = (
            f"Pace: {pace.upper()}\n"
            f"  - {min_act}-{max_act} activities per day\n"
            f"  - {min_dur}-{max_dur} minutes per activity\n"
            f"  - {pp['buffer_between_activities']}-minute buffers between activities\n"
            f"  - {pp['lunch_duration']}-minute lunch, {pp['dinner_duration']}-minute dinner"
        )

        transport = ", ".join(prefs["transportation_modes"])
        interests = ", ".join(prefs["interests"])
        dietary = ", ".join(prefs.get("dietary_restrictions", [])) or "None"

        return (
            f"Generate a complete day-by-day itinerary for a trip to "
            f"{prefs['city']}, {prefs['country']}.\n\n"
            f"**Trip Details:**\n"
            f"- Starting location: {prefs['starting_location']}\n"
            f"- Location preference: {prefs['location_preference']}\n"
            f"- Dates: {prefs['start_date']} to {prefs['end_date']} "
            f"({prefs['duration_days']} days)\n"
            f"- Hours per day: {prefs['hours_per_day']}\n"
            f"- Budget: ${prefs['budget']:.2f} total "
            f"(${prefs['daily_budget']:.2f}/day) {prefs['budget_currency']}\n"
            f"- Transportation: {transport}\n"
            f"- {pace_block}\n\n"
            f"**Preferences:**\n"
            f"- Interests: {interests}\n"
            f"- Dietary restrictions: {dietary}\n"
            f"- Group: {prefs.get('group_type', 'not specified')}"
            f"{', ' + str(prefs['group_size']) + ' people' if prefs.get('group_size') else ''}\n\n"
            f"Return the itinerary JSON now."
        )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_gemini_response(
        self, text: str, request_id: str
    ) -> Dict[str, Any]:
        """Extract and parse the JSON body from the Gemini response."""
        cleaned = text.strip()

        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start != -1 and end > start:
                cleaned = cleaned[start:end]

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            self.logger.error(
                "Failed to parse Gemini JSON",
                extra={"request_id": request_id, "error": str(exc), "preview": cleaned[:500]},
            )
            raise ItineraryGenerationError(
                reason=f"Invalid JSON from Gemini: {exc}",
                constraints={"raw_preview": cleaned[:1000]},
            )

        # Normalise wrapper key
        if "itinerary" not in data and "days" in data:
            data = {"itinerary": data}

        return data

    # ------------------------------------------------------------------
    # Object builder
    # ------------------------------------------------------------------

    def _build_itinerary_object(
        self,
        raw: Dict[str, Any],
        prefs: Dict[str, Any],
        request_id: str,
    ) -> Itinerary:
        """Convert the parsed JSON into an Itinerary dataclass."""
        itin = raw.get("itinerary", raw)
        trip_id = prefs.get("trip_id", f"trip_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        days: List[ItineraryDay] = []
        for day_raw in itin.get("days", []):
            # Activities
            activities: List[Activity] = []
            for idx, a in enumerate(day_raw.get("activities", [])):
                activities.append(
                    Activity(
                        activity_id=f"{trip_id}_d{day_raw.get('day', 0)}_a{idx + 1}",
                        venue_name=a.get("venue_name", ""),
                        sequence=idx + 1,
                        planned_start=a.get("time_start", ""),
                        planned_end=a.get("time_end", ""),
                        category=a.get("category"),
                        notes=a.get("notes"),
                        duration_reason=a.get("duration_reason"),
                        estimated_cost=float(a.get("cost", 0)),
                    )
                )

            # Meals
            meals: List[Meal] = []
            for m in day_raw.get("meals", []):
                meals.append(
                    Meal(
                        meal_type=m.get("meal_type", ""),
                        venue_name=m.get("venue_name", ""),
                        planned_time=m.get("time", ""),
                        estimated_cost=float(m.get("cost", 0)),
                    )
                )

            # Travel segments
            morning = None
            if dep := day_raw.get("morning_departure"):
                morning = TravelSegment(
                    mode=dep.get("mode", ""),
                    duration_minutes=int(dep.get("travel_minutes", 0)),
                    from_location=dep.get("from", ""),
                    to_location=dep.get("to", ""),
                )
            evening = None
            if ret := day_raw.get("evening_return"):
                evening = TravelSegment(
                    mode=ret.get("mode", ""),
                    duration_minutes=int(ret.get("travel_minutes", 0)),
                    from_location=ret.get("from", ""),
                    to_location=ret.get("to", ""),
                )

            days.append(
                ItineraryDay(
                    day_number=day_raw.get("day", len(days) + 1),
                    date=day_raw.get("date", ""),
                    morning_departure=morning,
                    evening_return=evening,
                    activities=activities,
                    meals=meals,
                    daily_budget_allocated=float(
                        day_raw.get("daily_budget_allocated", prefs["daily_budget"])
                    ),
                    daily_budget_spent=float(day_raw.get("daily_budget_spent", 0)),
                    total_activities=len(activities),
                )
            )

        total_spent = sum(d.daily_budget_spent for d in days)

        return Itinerary(
            trip_id=trip_id,
            itinerary_version=1,
            created_at=datetime.now().isoformat(),
            status="draft",
            days=days,
            total_budget=float(prefs["budget"]),
            total_spent=total_spent,
            total_activities=sum(d.total_activities for d in days),
            activities_per_day_avg=float(itin.get("activities_per_day_avg", 0)),
            total_travel_time_hours=float(itin.get("total_travel_time_hours", 0)),
            pace=prefs["pace"],
        )

    # ------------------------------------------------------------------
    # Feasibility validation
    # ------------------------------------------------------------------

    def _validate_feasibility(
        self,
        itinerary: Itinerary,
        prefs: Dict[str, Any],
        request_id: str,
    ) -> Dict[str, Any]:
        """Check that the generated itinerary meets constraints."""
        issues: List[str] = []
        warnings: List[str] = []
        expected_days = prefs["duration_days"]
        pp = settings.PACE_PARAMS[prefs["pace"]]

        # Day count
        if len(itinerary.days) != expected_days:
            issues.append(
                f"Expected {expected_days} days, got {len(itinerary.days)}"
            )

        for day in itinerary.days:
            tag = f"Day {day.day_number}"

            if not day.activities:
                issues.append(f"{tag}: no activities scheduled")

            if len(day.meals) < 2:
                warnings.append(f"{tag}: only {len(day.meals)} meal(s) (expected 2+)")

            # Budget (10 % tolerance per day)
            if day.daily_budget_spent > day.daily_budget_allocated * 1.10:
                issues.append(
                    f"{tag}: budget exceeded "
                    f"(${day.daily_budget_spent:.2f} > ${day.daily_budget_allocated:.2f})"
                )

            # Activity count vs. pace
            lo, hi = pp["activities_per_day"]
            n = len(day.activities)
            if n < lo or n > hi:
                warnings.append(
                    f"{tag}: {n} activities (expected {lo}-{hi} for {prefs['pace']} pace)"
                )

        # Total budget (5 % tolerance)
        if itinerary.total_spent > itinerary.total_budget * 1.05:
            issues.append(
                f"Total budget exceeded (${itinerary.total_spent:.2f} > "
                f"${itinerary.total_budget:.2f})"
            )

        # Interest coverage
        used = {a.category for d in itinerary.days for a in d.activities if a.category}
        missing = [i for i in prefs["interests"] if i not in used]
        if missing:
            warnings.append(f"Interests not covered: {missing}")

        feasible = len(issues) == 0
        result = {
            "feasible": feasible,
            "issues": issues,
            "warnings": warnings,
        }
        log = self.logger.info if feasible else self.logger.warning
        log(
            "Feasibility %s", "passed" if feasible else "FAILED",
            extra={"request_id": request_id, "issues": len(issues), "warnings": len(warnings)},
        )
        return result


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    async def _self_test():
        print("=" * 72)
        print("  ITINERARY SERVICE — SELF-TEST")
        print("=" * 72)

        test_input = {
            "city": "Kingston",
            "country": "Canada",
            "start_date": "2026-05-10",
            "end_date": "2026-05-17",
            "duration_days": 7,
            "budget": 2500.0,
            "budget_currency": "CAD",
            "interests": [
                "museums", "food tours", "historic landmarks",
                "art galleries", "cafes",
            ],
            "pace": "moderate",
            "location_preference": "City center near public transportation",
        }

        print("\n[INPUT]")
        print(json.dumps(test_input, indent=2))

        svc = ItineraryService()

        # Validate
        print("\n[1] Validating preferences ...")
        validated = svc._validate_preferences(test_input, "selftest")
        print(f"    ✓ Daily budget: ${validated['daily_budget']:.2f}")
        print(f"    ✓ Duration: {validated['duration_days']} days")
        print(f"    ✓ Pace: {validated['pace']}")

        # Build prompt
        print("\n[2] Building Gemini prompt ...")
        prompt = svc._build_generation_prompt(validated)
        print(f"    ✓ Prompt length: {len(prompt)} chars")

        # Call Gemini (if key present)
        if not settings.GEMINI_KEY:
            print("\n[SKIP] GEMINI_KEY not set — skipping API call")
            print("       Add GEMINI_KEY to backend/.env to run the full test.")
            print("\n" + "=" * 72)
            print("  PARTIAL SELF-TEST PASSED ✓")
            print("=" * 72)
            return

        print("\n[3] Calling Gemini API (may take 30-60 s) ...")
        itinerary = await svc.generate_itinerary(test_input, "selftest")

        print(f"\n    ✓ Itinerary generated!")
        print(f"      Days:       {len(itinerary.days)}")
        print(f"      Activities: {itinerary.total_activities}")
        print(f"      Avg/day:    {itinerary.activities_per_day_avg:.1f}")
        print(f"      Cost:       ${itinerary.total_spent:.2f} / ${itinerary.total_budget:.2f}")

        if itinerary.days:
            d = itinerary.days[0]
            print(f"\n    Day 1 — {d.date}")
            for a in d.activities:
                print(f"      {a.planned_start}-{a.planned_end}  {a.venue_name}  (${a.estimated_cost})")
            for m in d.meals:
                print(f"      {m.planned_time}  [{m.meal_type}] {m.venue_name}  (${m.estimated_cost})")

        out = "test_itinerary_output.json"
        with open(out, "w") as f:
            json.dump(itinerary.to_dict(), f, indent=2)
        print(f"\n    ✓ Saved full output to {out}")

        print("\n" + "=" * 72)
        print("  FULL SELF-TEST PASSED ✓")
        print("=" * 72)

    asyncio.run(_self_test())
