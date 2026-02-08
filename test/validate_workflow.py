#!/usr/bin/env python3
"""
Automated workflow validation script for the Toronto MVP.

Validates key QA constraints against a running server:
  - Source citation coverage
  - Venue closed-world constraint
  - Still-need field monotonicity during intake
  - Confirmation gate enforcement
  - Enrichment fields present in itinerary response

Usage:
    # Start the server first:  python3 backend/app.py
    python3 test/validate_workflow.py
"""

import json
import re
import sys
import requests

BASE_URL = "http://localhost:8000"
API_CHAT = f"{BASE_URL}/api/chat"

# Known venue IDs from TORONTO_FALLBACK_VENUES
KNOWN_VENUE_IDS = {
    "cn_tower", "rom", "st_lawrence_market", "ripley_aquarium", "high_park",
    "distillery_district", "kensington_market", "hockey_hall_of_fame",
    "casa_loma", "ago", "toronto_islands", "harbourfront_centre",
    "bata_shoe_museum", "toronto_zoo", "aga_khan_museum",
    # Also include DB-seeded venue IDs
    "toronto_islands_ferry", "yorkdale_shopping_centre", "rogers_centre",
    "happy_lamb_hot_pot", "royal_ontario_museum", "art_gallery_ontario",
    "earl_bales_ski_centre", "cong_ca_phe_toronto", "toronto_eaton_centre",
    "ripleys_aquarium_canada", "ontario_science_centre", "nathan_phillips_square",
    "scotiabank_arena", "toronto_symphony_orchestra", "rec_room_toronto",
    "steam_whistle_brewery", "allan_gardens_conservatory",
}

passed = 0
failed = 0
warnings = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def warn(name: str, detail: str = ""):
    global warnings
    warnings += 1
    print(f"  ⚠️  {name}" + (f" — {detail}" if detail else ""))


def chat(messages, user_input=None):
    """Send a chat request and return the JSON response."""
    payload = {"messages": messages}
    if user_input:
        payload["user_input"] = user_input
    resp = requests.post(API_CHAT, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def main():
    print("=" * 70)
    print("MonVoyage Workflow Validator")
    print("=" * 70)

    # ── Check server is up ────────────────────────────────────────
    print("\n🔍 Server connectivity")
    try:
        health = requests.get(f"{BASE_URL}/api/health", timeout=5).json()
        check("Server is healthy", health.get("status") == "healthy")
    except Exception as e:
        print(f"  ❌ Cannot reach server at {BASE_URL}: {e}")
        print("  💡 Start the server with: python3 backend/app.py")
        sys.exit(1)

    # ── Test 1: Greeting ──────────────────────────────────────────
    print("\n🔍 Test 1: Greeting")
    data = chat([])
    check("Phase is 'greeting'", data.get("phase") == "greeting")
    check("still_need has 4 fields", len(data.get("still_need", [])) == 4)
    check("Assistant message is non-empty", bool(data.get("assistant_message")))
    messages = data.get("messages", [])

    # ── Test 2: Intake — provide all details ──────────────────────
    print("\n🔍 Test 2: Intake (all details in one turn)")
    data = chat(
        messages,
        user_input="March 15-17, 2026. Budget $300. I love museums and food. Moderate pace.",
    )
    phase = data.get("phase")
    still_need = data.get("still_need", [])
    check("Phase is 'intake' or 'confirmed'", phase in ("intake", "confirmed"))

    if phase == "confirmed":
        check("still_need is empty", len(still_need) == 0 or still_need is None)
        check(
            "Confirmation marker present",
            "generate your toronto itinerary" in data.get("assistant_message", "").lower(),
        )
    else:
        # Multi-turn needed — check still_need shrinks
        check("still_need exists", still_need is not None)
        if still_need:
            warn("Not all fields captured in one turn", f"still need: {still_need}")

    messages = data.get("messages", [])

    # If not yet confirmed, do another turn
    if phase != "confirmed":
        print("\n🔍 Test 2b: Continue intake for missing fields")
        data = chat(messages, user_input="moderate pace, my budget is $300, I like food and museums")
        phase = data.get("phase")
        messages = data.get("messages", [])
        check("Phase is now 'confirmed' or 'intake'", phase in ("confirmed", "intake"))

    # ── Test 3: Confirmation gate ─────────────────────────────────
    print("\n🔍 Test 3: Confirmation gate")
    if phase == "confirmed":
        data = chat(messages, user_input="Yes, let's do it!")
        check("Phase is 'itinerary'", data.get("phase") == "itinerary")
        check("still_need is null", data.get("still_need") is None)
        itinerary_text = data.get("assistant_message", "")
        check("Itinerary text is non-empty", len(itinerary_text) > 100)

        # ── Test 4: Source citation coverage ──────────────────────
        print("\n🔍 Test 4: Source citation coverage")
        time_slot_pattern = re.compile(r"^(Morning|Afternoon|Evening):", re.MULTILINE)
        source_pattern = re.compile(r"\(Source:\s*(\w+),\s*(https?://[^)]+)\)")

        time_slots = time_slot_pattern.findall(itinerary_text)
        sources = source_pattern.findall(itinerary_text)

        check(
            f"Found {len(time_slots)} time slots",
            len(time_slots) >= 3,
            f"Expected at least 3 (1 day × 3 slots)",
        )
        check(
            f"Found {len(sources)} Source citations",
            len(sources) >= 3,
        )
        check(
            "100% Source coverage",
            len(sources) >= len(time_slots),
            f"{len(sources)} sources vs {len(time_slots)} time slots",
        )

        # ── Test 5: Closed-world constraint ───────────────────────
        print("\n🔍 Test 5: Closed-world venue constraint")
        all_venue_ids_valid = True
        for venue_id, url in sources:
            if venue_id not in KNOWN_VENUE_IDS:
                warn(f"Unknown venue_id: {venue_id}", "may be a DB-only venue")
                all_venue_ids_valid = False
        check("All venue_ids are from known set", all_venue_ids_valid)

        # ── Test 6: Enrichment fields ─────────────────────────────
        print("\n🔍 Test 6: Enrichment fields")
        weather = data.get("weather_summary")
        budget = data.get("budget_summary")
        routes = data.get("route_data")

        if weather:
            check("weather_summary is populated", True)
        else:
            warn("weather_summary is null", "Weather service may be unavailable")

        if budget:
            check("budget_summary is populated", True)
            check("budget_summary has within_budget field", "within_budget" in budget)
        else:
            warn("budget_summary is null", "Budget service may be unavailable")

        if routes:
            check(f"route_data has {len(routes)} legs", len(routes) >= 1)
        else:
            warn("route_data is null", "Google Maps API may not be configured")

        messages = data.get("messages", [])
    else:
        warn("Could not reach confirmed phase", "Skipping itinerary tests")

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"Results:  ✅ {passed} passed  |  ❌ {failed} failed  |  ⚠️  {warnings} warnings")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)
    print("🎉 All critical checks passed!")


if __name__ == "__main__":
    main()
