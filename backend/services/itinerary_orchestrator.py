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
from services.trip_budget_service import TripBudgetService
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
You are a Toronto travel itinerary generator. You MUST ONLY use venues from \
the venue list below. This is a hard constraint — do NOT invent venues.

VENUE LIST — START
{venue_catalogue}
VENUE LIST — END
{weather_context}
Rules:
1. Every Morning/Afternoon/Evening line MUST include a Source citation in \
this exact format:
   Source: <venue_id>, <url>
   where venue_id and url come from the venue list above.
2. Use this exact output format:

Day 1
Morning: <activity description> — <venue_name> (Source: <venue_id>, <url>)
Afternoon: <activity description> — <venue_name> (Source: <venue_id>, <url>)
Evening: <activity description> — <venue_name> (Source: <venue_id>, <url>)

Day 2
...

3. CLOSED-WORLD RULE: If the user asked for something that is NOT in the \
venue list, refuse to invent it. Instead say you don't have it and offer \
2-3 closest alternatives that ARE in the list (with Source citations).
4. Do NOT add facts about a venue (prices, opening hours, events) unless \
that information is present in the venue record above. Keep descriptions \
generic if unsure.
5. 100% SOURCE COVERAGE: Every single time-slot line must have a Source. \
No exceptions.
6. Respect the user's stated dates, budget, interests, and pace when \
choosing venues and structuring the days.\
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

        # Budget — uses Airbnb scraping + hardcoded flight prices, no key
        try:
            self.budget_service: Optional[TripBudgetService] = TripBudgetService()
        except Exception as exc:
            logger.warning("TripBudgetService init failed: %s", exc)
            self.budget_service = None

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
            "ItineraryOrchestrator initialised — weather=%s budget=%s maps=%s venues=%s",
            self.weather_service is not None,
            self.budget_service is not None,
            self.maps_service is not None and self.maps_service.is_available(),
            self.venue_service is not None,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_enriched_itinerary(
        self,
        messages: List[Dict[str, str]],
        llm_caller: Callable[..., str],
        use_groq: bool = True,
        use_gemini: bool = False,
        groq_client: Any = None,
        gemini_client: Any = None,
    ) -> Dict[str, Any]:
        """Run the full enrichment pipeline and return an enriched result dict.

        Returns
        -------
        dict with keys:
            itinerary_text   — LLM-generated itinerary (str, always present)
            weather_summary  — human-readable weather line (str | None)
            budget_summary   — budget dict (dict | None)
            route_data       — list of route legs (list | None)
        """
        loop = asyncio.get_running_loop()

        # ── State C: extract structured preferences ──────────────────
        preferences = self._extract_preferences_from_history(messages)
        logger.info("Extracted preferences: %s", preferences.to_dict())

        # ── State D.1: parallel enrichment fetch ─────────────────────
        weather_result, budget_result, venues = await asyncio.gather(
            self._fetch_weather(loop, preferences),
            self._fetch_budget(loop, preferences),
            self._fetch_venues(loop),
            return_exceptions=True,
        )

        # Unwrap exceptions from gather
        if isinstance(weather_result, BaseException):
            logger.warning("Weather fetch raised: %s", weather_result)
            weather_result = None
        if isinstance(budget_result, BaseException):
            logger.warning("Budget fetch raised: %s", budget_result)
            budget_result = None
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
        itinerary_messages.append(
            {
                "role": "user",
                "content": (
                    "Please generate my Toronto itinerary now based on "
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
        route_data = await self._fetch_routes(loop, itinerary_text)

        # ── State E: assemble response ───────────────────────────────
        weather_summary = self._format_weather_summary(weather_result)
        budget_summary = self._format_budget_summary(budget_result)

        return {
            "itinerary_text": itinerary_text,
            "weather_summary": weather_summary,
            "budget_summary": budget_summary,
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
            city="Toronto",
            country="Canada",
            start_date=start_date,
            end_date=end_date,
            duration_days=duration_days,
            budget=budget,
            budget_currency="CAD",
            interests=interests if interests else ["Culture and History"],
            pace=pace or "moderate",
            location_preference="downtown Toronto",
            booking_type="none",      # Toronto-only MVP — no transport booking
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

    async def _fetch_budget(
        self, loop: asyncio.AbstractEventLoop, prefs: TripPreferences,
    ) -> Optional[Dict[str, Any]]:
        """Fetch budget estimation; returns None on any failure."""
        if not self.budget_service:
            return None
        try:
            result = await loop.run_in_executor(
                None, self.budget_service.estimate_trip_budget, prefs
            )
            if result.get("error"):
                logger.warning("BudgetService returned error: %s", result["error"])
                return None
            return result
        except Exception as exc:
            logger.warning("Budget fetch failed: %s", exc)
            return None

    async def _fetch_venues(
        self, loop: asyncio.AbstractEventLoop,
    ) -> List[Dict[str, Any]]:
        """Fetch Toronto venues (DB or fallback). Always returns a list."""
        if self.venue_service:
            try:
                venues = await loop.run_in_executor(
                    None, self.venue_service.get_toronto_venues,
                )
                if venues:
                    return venues
            except Exception as exc:
                logger.warning("VenueService.get_toronto_venues failed: %s", exc)
        return list(TORONTO_FALLBACK_VENUES)

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
    ) -> Optional[List[Dict[str, Any]]]:
        """Extract venue names from itinerary text and fetch routes."""
        if not self.maps_service or not self.maps_service.is_available():
            return None

        venue_names = self._extract_venue_names_from_itinerary(itinerary_text)
        if len(venue_names) < 2:
            return None

        try:
            routes = await loop.run_in_executor(
                None,
                lambda: self.maps_service.get_itinerary_routes(
                    venue_names, city="Toronto", country="Canada", mode="transit"
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
        """Build optional weather context block for the LLM prompt."""
        if not weather_result or not weather_result.get("forecasts"):
            return "\n"

        lines = ["\n\nWEATHER FORECAST — consider these conditions when planning activities:"]
        for f in weather_result["forecasts"]:
            lines.append(
                f"  {f['date']}: {f['condition']}, "
                f"{f['temp_min_c']}°C to {f['temp_max_c']}°C, "
                f"precipitation {f['precipitation_chance']}%"
            )
        lines.append(
            "If rain is likely (>50%), prefer indoor venues. "
            "If cold (<5°C), mention dressing warmly.\n"
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
    def _format_budget_summary(
        budget_result: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Produce a compact budget summary dict for the API response."""
        if not budget_result:
            return None

        est = budget_result.get("estimation")
        if not est:
            return None

        return {
            "within_budget": est.get("within_budget", False),
            "cheapest_total": est.get("cheapest_total", {}).get("total"),
            "average_total": est.get("average_total", {}).get("total"),
            "remaining_budget": est.get("remaining_at_cheapest"),
            "links": est.get("links"),
        }

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
