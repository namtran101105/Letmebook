"""
Itinerary Orchestrator — coordinates venue fetch, weather, budget, LLM
itinerary generation, and route enrichment into a single enriched response.

This module implements States C, D, and E of the workflow:
    C. Build Request   — extract structured TripPreferences from conversation
    D. Generate+Enrich — parallel service calls + LLM itinerary + routes
    E. Response Assembly — combine all results into a single dict

All enrichment services (weather, budget, routes) are fail-soft: a failure
in any one of them never blocks itinerary generation.  Only an LLM failure
is fatal.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from models.trip_preferences import TripPreferences
from services.venue_service import VenueService, TORONTO_FALLBACK_VENUES
from services.weather_service import WeatherService
from services.booking_service import BookingService
from services.google_maps_service import GoogleMapsService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Month-name helpers for regex extraction
# ---------------------------------------------------------------------------

_MONTH_NAMES = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7,
    "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12,
    "dec": 12,
}

# E.g. "March 15-17, 2026"  or  "March 15 - 17, 2026"
_DATE_RANGE_MONTH = re.compile(
    r"(?P<month>[A-Za-z]+)\s+(?P<d1>\d{1,2})\s*[-–to]+\s*(?P<d2>\d{1,2})"
    r"(?:\s*,?\s*(?P<year>\d{4}))?",
    re.IGNORECASE,
)

# E.g. "2026-03-15 to 2026-03-17"
_DATE_RANGE_ISO = re.compile(
    r"(?P<y1>\d{4})-(?P<m1>\d{2})-(?P<d1>\d{2})"
    r"\s*(?:to|-|–)\s*"
    r"(?P<y2>\d{4})-(?P<m2>\d{2})-(?P<d2>\d{2})"
)

# E.g. "March 15 to March 20, 2026"  or  "March 15, 2026 to March 20, 2026"
_DATE_RANGE_TWO_MONTHS = re.compile(
    r"(?P<month1>[A-Za-z]+)\s+(?P<d1>\d{1,2})(?:\s*,?\s*(?P<y1>\d{4}))?"
    r"\s*(?:to|-|–)\s*"
    r"(?P<month2>[A-Za-z]+)\s+(?P<d2>\d{1,2})(?:\s*,?\s*(?P<y2>\d{4}))?",
    re.IGNORECASE,
)

# Budget: "$300", "300 CAD", "budget $300", "budget is $500", "$1,200"
_BUDGET_PATTERN = re.compile(
    r"\$\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)"
    r"|(?P<amount2>[\d,]+(?:\.\d{1,2})?)\s*(?:CAD|cad|dollars?|bucks)",
    re.IGNORECASE,
)

# Pace keywords
_PACE_PATTERN = re.compile(
    r"\b(relaxed|relax|chill|easy|laid.?back|moderate|medium|balanced|normal"
    r"|packed|fast|rush|busy|intense|active|jam.?packed|hectic)\b",
    re.IGNORECASE,
)


# ── Itinerary system prompt (extended with weather context) ───────────

ITINERARY_SYSTEM_PROMPT_TEMPLATE = """\
You are a travel itinerary generator. ONLY use venues from the list below.

VENUE LIST — START
{venue_catalogue}
VENUE LIST — END
{weather_context}
STRICT OUTPUT RULES:
1. Each day MUST have EXACTLY 2 meals: Lunch and Dinner \
(use food/restaurant venues from the list).
2. Activities per day (NON-MEAL time slots) based on pace:
   - relaxed pace: 2 activities (Morning + Afternoon)
   - moderate pace: 3 activities (Morning + Afternoon + Evening)
   - packed pace: 4 activities (Early Morning + Morning + Afternoon + Evening)
3. Every single line MUST include a Source citation in this exact format:
   (Source: <venue_id>, <url>)
4. Use this exact format per day:

Day 1 — [Date]
Morning: <activity> — <venue_name> (Source: <venue_id>, <url>)
Lunch: <meal description> — <restaurant_name> (Source: <venue_id>, <url>)
Afternoon: <activity> — <venue_name> (Source: <venue_id>, <url>)
Dinner: <meal description> — <restaurant_name> (Source: <venue_id>, <url>)

(For moderate pace add Evening activity before Dinner; \
for packed pace add Early Morning before Morning.)

Day 2
...

5. CLOSED-WORLD RULE: Never invent venues. Only use venues from the list.
6. Do NOT add facts not present in the venue record (prices, hours, events).
7. 100% SOURCE COVERAGE: Every line must have a Source. No exceptions.
8. Respect the user's stated dates, interests, and pace.
9. At the very end, add:

## Estimated Budget
- Accommodation (per night): ~$X CAD
- Activities total: ~$X CAD
- Meals total: ~$X CAD
- **Estimated Total: ~$X CAD**
(Based on average tourist prices in the destination city)\
"""


class ItineraryOrchestrator:
    """Orchestrates venue fetch, weather, budget, LLM itinerary, and routes.

    All enrichment services are initialised eagerly but fail gracefully — if
    a service cannot be created (e.g. missing API key) the corresponding
    enrichment field is simply ``None`` in the response.
    """

    def __init__(self) -> None:
        # Weather — Open-Meteo, no API key required
        try:
            self.weather_service: Optional[WeatherService] = WeatherService()
        except Exception as exc:
            logger.warning("WeatherService init failed: %s", exc)
            self.weather_service = None

        # Booking — Airbnb + Skyscanner links
        try:
            self.booking_service: Optional[BookingService] = BookingService()
        except Exception as exc:
            logger.warning("BookingService init failed: %s", exc)
            self.booking_service = None

        # Google Maps — requires GOOGLE_MAPS_API_KEY; graceful if missing
        try:
            self.maps_service: Optional[GoogleMapsService] = GoogleMapsService()
        except Exception as exc:
            logger.warning("GoogleMapsService init failed: %s", exc)
            self.maps_service = None

        # Venues — DB or fallback
        try:
            self.venue_service: Optional[VenueService] = VenueService()
        except Exception:
            logger.warning("VenueService init failed — will use fallback venues")
            self.venue_service = None

        logger.info(
            "ItineraryOrchestrator initialised — weather=%s booking=%s maps=%s venues=%s",
            self.weather_service is not None,
            self.booking_service is not None,
            self.maps_service is not None and self.maps_service.is_available(),
            self.venue_service is not None,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_enriched_itinerary(
        self,
        messages: List[Dict[str, str]],
        llm_caller: Callable[..., str] = None,
        use_groq: bool = True,
        use_gemini: bool = False,
        groq_client: Any = None,
        gemini_client: Any = None,
        booking_type: str = "none",
        source_location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the full enrichment pipeline and return an enriched result dict.

        Returns
        -------
        dict with keys:
            itinerary_text  — LLM-generated itinerary (str, always present)
            weather_summary — human-readable weather line (str | None)
            booking_links   — dict with flight/airbnb URLs (dict | None)
            route_data      — list of route legs (list | None)
        """
        loop = asyncio.get_running_loop()

        # ── State C: extract structured preferences ──────────────────
        preferences = self._extract_preferences_from_history(messages)
        logger.info("Extracted preferences: %s", preferences.to_dict())

        # ── State D.1: parallel enrichment fetch ─────────────────────
        weather_result, venues, booking_result = await asyncio.gather(
            self._fetch_weather(loop, preferences),
            self._fetch_venues(loop, preferences.city),
            self._fetch_booking(loop, preferences, booking_type, source_location),
            return_exceptions=True,
        )

        # Unwrap exceptions from gather
        if isinstance(weather_result, BaseException):
            logger.warning("Weather fetch raised: %s", weather_result)
            weather_result = None
        if isinstance(booking_result, BaseException):
            logger.warning("Booking fetch raised: %s", booking_result)
            booking_result = None
        if isinstance(venues, BaseException):
            logger.warning("Venue fetch raised: %s", venues)
            venues = list(TORONTO_FALLBACK_VENUES)

        # ── State D.2: build prompt and call LLM ─────────────────────
        # Sort venues by place_key for deterministic ordering
        if venues:
            venues = sorted(venues, key=lambda v: v.get("place_key", ""))

        venue_catalogue = VenueService.format_venues_for_chat(venues)

        # Build optional weather context for the LLM
        weather_context = self._build_weather_context(weather_result)

        itinerary_system = ITINERARY_SYSTEM_PROMPT_TEMPLATE.format(
            venue_catalogue=venue_catalogue,
            weather_context=weather_context,
        )

        # Build the messages list for the itinerary LLM call
        itinerary_messages: List[Dict[str, str]] = [
            {"role": "system", "content": itinerary_system},
        ]
        for m in messages:
            if m["role"] != "system":
                itinerary_messages.append(m)
        
        # Build dynamic city reference for user message
        city_name = preferences.city if preferences.city else "the destination"
        
        itinerary_messages.append(
            {
                "role": "user",
                "content": (
                    f"Please generate my {city_name} itinerary now based on "
                    "everything I told you. Use ONLY venues from the venue "
                    "list and include Source citations on every line."
                ),
            }
        )

        # Call LLM (fatal if fails)
        itinerary_text = await self._call_llm(
            loop, itinerary_messages,
            use_groq=use_groq, use_gemini=use_gemini,
            groq_client=groq_client, gemini_client=gemini_client,
        )

        # ── State D.3: route enrichment (post-LLM) ──────────────────
        route_data = await self._fetch_routes(loop, itinerary_text, preferences)

        # ── State E: assemble response ───────────────────────────────
        weather_summary = self._format_weather_summary(weather_result)

        return {
            "itinerary_text": itinerary_text,
            "weather_summary": weather_summary,
            "booking_links": self._format_booking_links(booking_result),
            "route_data": route_data,
        }

    # ------------------------------------------------------------------
    # State C — preference extraction (regex-based, no LLM call)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_preferences_from_history(
        messages: List[Dict[str, str]],
    ) -> TripPreferences:
        """Parse dates, budget, interests, pace from the conversation turns.

        Scans *all* user messages in order so that later corrections
        overwrite earlier values.
        """
        start_date: Optional[str] = None
        end_date: Optional[str] = None
        budget: Optional[float] = None
        interests: List[str] = []
        pace: Optional[str] = None

        user_texts: List[str] = [
            m["content"] for m in messages if m.get("role") == "user"
        ]
        combined = " ".join(user_texts)

        # -- Dates -----------------------------------------------------------
        # Try ISO range first: "2026-03-15 to 2026-03-17"
        m = _DATE_RANGE_ISO.search(combined)
        if m:
            start_date = f"{m.group('y1')}-{m.group('m1')}-{m.group('d1')}"
            end_date = f"{m.group('y2')}-{m.group('m2')}-{m.group('d2')}"
        else:
            # Try "March 15 to March 20, 2026"
            m = _DATE_RANGE_TWO_MONTHS.search(combined)
            if m:
                mo1 = _MONTH_NAMES.get(m.group("month1").lower())
                mo2 = _MONTH_NAMES.get(m.group("month2").lower())
                year = m.group("y2") or m.group("y1") or str(datetime.now().year)
                if mo1 and mo2:
                    start_date = f"{year}-{mo1:02d}-{int(m.group('d1')):02d}"
                    end_date = f"{year}-{mo2:02d}-{int(m.group('d2')):02d}"
            else:
                # Try "March 15-17, 2026"
                m = _DATE_RANGE_MONTH.search(combined)
                if m:
                    month_num = _MONTH_NAMES.get(m.group("month").lower())
                    year = m.group("year") or str(datetime.now().year)
                    if month_num:
                        start_date = f"{year}-{month_num:02d}-{int(m.group('d1')):02d}"
                        end_date = f"{year}-{month_num:02d}-{int(m.group('d2')):02d}"
        # -- City and Country ------------------------------------------------
        city: Optional[str] = None
        country: Optional[str] = None
        
        # Try to extract city/country from conversation
        # Look for patterns like "visiting Paris", "trip to London", "traveling to Tokyo"
        city_patterns = [
            r"(?:visit|visiting|trip to|traveling to|travel to|going to|go to|head to|headed to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:trip|itinerary)",
            r"in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)(?:\s|,|\.|!|\?|$)",
        ]
        
        for pattern in city_patterns:
            match_obj = re.search(pattern, combined)
            if match_obj:
                potential_city = match_obj.group(1).strip()
                # Simple filter: skip common non-city words
                if potential_city.lower() not in ["march", "april", "may", "june", "july", "august", 
                                                    "september", "october", "november", "december",
                                                    "relaxed", "moderate", "packed", "weekend", 
                                                    "canada", "france", "italy", "spain", "uk", "usa"]:
                    city = potential_city
                    break
        
        # Try to extract country (look for pattern like "Paris, France" or "in France")
        if city:
            country_pattern = rf"{city}(?:,\s*|\sin\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
            country_match = re.search(country_pattern, combined)
            if country_match:
                country = country_match.group(1).strip()
        
        # Fallback: Default to Toronto if no city extracted
        if not city:
            logger.warning("No city extracted from conversation, defaulting to Toronto")
            city = "Toronto"
            country = "Canada"
        # -- Budget ----------------------------------------------------------
        for bm in _BUDGET_PATTERN.finditer(combined):
            raw = (bm.group("amount") or bm.group("amount2") or "").replace(",", "")
            if raw:
                try:
                    budget = float(raw)
                except ValueError:
                    pass

        # -- Interests -------------------------------------------------------
        interest_kws = TripPreferences.INTEREST_KEYWORDS
        combined_lower = combined.lower()
        found_cats: set = set()
        for kw, cat in interest_kws.items():
            if kw in combined_lower:
                found_cats.add(cat)
        interests = sorted(found_cats)

        # -- Pace ------------------------------------------------------------
        pm = _PACE_PATTERN.search(combined)
        if pm:
            pace_raw = pm.group(1).lower().replace("-", "").replace(" ", "")
            pace = TripPreferences.PACE_SYNONYMS.get(pace_raw, pace_raw)

        # -- Duration --------------------------------------------------------
        duration_days: Optional[int] = None
        if start_date and end_date:
            try:
                sd = datetime.strptime(start_date, "%Y-%m-%d")
                ed = datetime.strptime(end_date, "%Y-%m-%d")
                duration_days = (ed - sd).days + 1  # inclusive
            except ValueError:
                pass

        return TripPreferences(
            city=city,           # Use extracted city
            country=country,     # Use extracted country
            start_date=start_date,
            end_date=end_date,
            duration_days=duration_days,
            budget=budget,
            budget_currency="CAD",
            interests=interests if interests else [],
            pace=pace or "moderate",
            location_preference=f"downtown {city}" if city else "downtown",
            booking_type="none",
            source_location=None,
        )

    # ------------------------------------------------------------------
    # State D — parallel enrichment helpers
    # ------------------------------------------------------------------

    async def _fetch_weather(
        self, loop: asyncio.AbstractEventLoop, prefs: TripPreferences,
    ) -> Optional[Dict[str, Any]]:
        """Fetch weather data; returns None on any failure."""
        if not self.weather_service:
            return None
        try:
            result = await loop.run_in_executor(
                None, self.weather_service.get_trip_weather, prefs
            )
            if result.get("error"):
                logger.warning("WeatherService returned error: %s", result["error"])
                return None
            return result
        except Exception as exc:
            logger.warning("Weather fetch failed: %s", exc)
            return None

    async def _fetch_venues(
        self,
        loop: asyncio.AbstractEventLoop,
        city: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch venues for the specified city (DB or fallback). Always returns a list."""
        if not city:
            city = "Toronto"  # Default fallback

        if self.venue_service:
            try:
                venues = await loop.run_in_executor(
                    None,
                    lambda: self.venue_service.get_all_venues_for_city(city, limit=50),
                )
                if venues:
                    return venues
            except Exception as exc:
                logger.warning("VenueService.get_all_venues_for_city failed for %s: %s", city, exc)

        # Fallback to Toronto venues if DB query fails or no venues found
        return list(TORONTO_FALLBACK_VENUES)

    async def _fetch_booking(
        self,
        loop: asyncio.AbstractEventLoop,
        prefs: TripPreferences,
        booking_type: str,
        source_location: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Trigger booking service for flight/Airbnb links; returns result or None."""
        if not self.booking_service or booking_type == "none":
            return None
        booking_prefs = TripPreferences(
            city=prefs.city,
            country=prefs.country,
            start_date=prefs.start_date,
            end_date=prefs.end_date,
            pace=prefs.pace,
            interests=prefs.interests,
            booking_type=booking_type,
            source_location=source_location,
        )
        try:
            return await loop.run_in_executor(
                None, self.booking_service.book_trip, booking_prefs
            )
        except Exception as exc:
            logger.warning("Booking fetch failed: %s", exc)
            return None

    async def _call_llm(
        self,
        loop: asyncio.AbstractEventLoop,
        itinerary_messages: List[Dict[str, str]],
        *,
        use_groq: bool,
        use_gemini: bool,
        groq_client: Any,
        gemini_client: Any,
    ) -> str:
        """Call the LLM for itinerary generation. Fatal if both fail."""
        response_text: str = ""

        if use_groq and groq_client:
            try:
                response_text = await loop.run_in_executor(
                    None,
                    lambda: groq_client.chat_with_history(
                        messages=itinerary_messages,
                        temperature=0.7,
                        max_tokens=4096,
                    ),
                )
            except Exception as exc:
                logger.warning("Groq LLM call failed, trying Gemini: %s", exc)

        if not response_text and use_gemini and gemini_client:
            try:
                response_text = await loop.run_in_executor(
                    None,
                    lambda: gemini_client.chat_with_history(
                        messages=itinerary_messages,
                        temperature=0.7,
                        max_tokens=4096,
                    ),
                )
            except Exception as exc:
                logger.error("Gemini LLM call also failed: %s", exc)

        # Last-resort: try the other LLM if neither was tried
        if not response_text and gemini_client and not use_gemini:
            try:
                response_text = await loop.run_in_executor(
                    None,
                    lambda: gemini_client.chat_with_history(
                        messages=itinerary_messages,
                        temperature=0.7,
                        max_tokens=4096,
                    ),
                )
            except Exception:
                pass

        if not response_text:
            raise RuntimeError("No LLM response — both Groq and Gemini failed")

        return response_text

    async def _fetch_routes(
        self,
        loop: asyncio.AbstractEventLoop,
        itinerary_text: str,
        preferences: TripPreferences,
    ) -> Optional[List[Dict[str, Any]]]:
        """Extract venue names from itinerary text and fetch routes."""
        if not self.maps_service or not self.maps_service.is_available():
            return None

        venue_names = self._extract_venue_names_from_itinerary(itinerary_text)
        if len(venue_names) < 2:
            return None

        try:
            # Get city and country from preferences for route calculation
            city = preferences.city or "Unknown City"
            country = preferences.country or "Unknown Country"
            
            routes = await loop.run_in_executor(
                None,
                lambda: self.maps_service.get_itinerary_routes(
                    venue_names, city=city, country=country, mode="transit"
                ),
            )
            return routes if routes else None
        except Exception as exc:
            logger.warning("Route fetch failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # State E — response formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _build_weather_context(
        weather_result: Optional[Dict[str, Any]],
    ) -> str:
        """Build day-by-day weather context for the LLM prompt."""
        if not weather_result or not weather_result.get("forecasts"):
            return "\n"

        lines = [
            "\n\nDAILY WEATHER FORECAST (CRITICAL - integrate into each day's planning):"
        ]
        for f in weather_result["forecasts"]:
            rain_notice = " [HIGH RAIN - prioritize indoor venues]" if f.get("precipitation_chance", 0) > 50 else ""
            cold_notice = " [COLD - mention warm clothing]" if f.get("temp_max_c", 20) < 5 else ""
            lines.append(
                f"  {f['date']}: {f['condition']}, "
                f"{f['temp_min_c']}°C to {f['temp_max_c']}°C, "
                f"precipitation {f['precipitation_chance']}%{rain_notice}{cold_notice}"
            )
        lines.append(
            "\nIMPORTANT: For each day in your itinerary, consider that day's specific weather:"
        )
        lines.append(
            "- If rain likely (>50%), choose indoor venues from the database (museums, indoor attractions)."
        )
        lines.append(
            "- If sunny and warm, outdoor venues are great."
        )
        lines.append(
            "- If cold (<5°C), mention wearing warm layers in your activity notes.\n"
        )
        return "\n".join(lines)

    @staticmethod
    def _format_weather_summary(
        weather_result: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Produce a compact one-line-per-day weather summary for the API response."""
        if not weather_result or not weather_result.get("forecasts"):
            return None

        parts = []
        for f in weather_result["forecasts"]:
            parts.append(
                f"{f['date']}: {f['condition']}, "
                f"{f['temp_min_c']}°C to {f['temp_max_c']}°C"
            )
        return " | ".join(parts)

    @staticmethod
    def _format_booking_links(
        booking_result: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, str]]:
        """Extract flight and Airbnb links from booking result for the API response."""
        if not booking_result or booking_result.get("skipped"):
            return None
        links: Dict[str, str] = {}
        accom = booking_result.get("accommodation")
        if accom and "airbnb_link" in accom:
            links["airbnb"] = accom["airbnb_link"]
        trans = booking_result.get("transportation")
        if trans:
            flights = trans.get("flights")
            if flights and "skyscanner_link" in flights:
                links["flight"] = flights["skyscanner_link"]
        return links if links else None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_venue_names_from_itinerary(text: str) -> List[str]:
        """Pull unique venue names from itinerary text (in order of appearance).

        Looks for the pattern:  ``— <venue_name> (Source:``
        """
        pattern = re.compile(r"—\s*(.+?)\s*\(Source:")
        seen: set = set()
        names: List[str] = []
        for m in pattern.finditer(text):
            name = m.group(1).strip()
            if name and name not in seen:
                seen.add(name)
                names.append(name)
        return names
