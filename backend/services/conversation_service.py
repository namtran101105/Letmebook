"""
Conversation service — manages the full multi-turn chat lifecycle for
itinerary planning.

Phases:
    1. greeting   — first response; warm welcome + ask for trip details
    2. intake     — collect dates, interests, pace over multiple turns
    3. confirmed  — all fields collected; waiting for user to say "yes"
    4. itinerary  — grounded day-by-day plan using Airflow venue data

The service is stateless on the server side: the full message history is
stored client-side and sent with every ``/api/chat`` request.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from clients.groq_client import GroqClient
from clients.gemini_client import GeminiClient
from services.venue_service import VenueService

if TYPE_CHECKING:
    from services.itinerary_orchestrator import ItineraryOrchestrator

logger = logging.getLogger(__name__)

# Type alias for the turn() return value:
#   (messages, assistant_text, phase, still_need, enrichment)
TurnResult = Tuple[
    List[Dict[str, str]],    # messages
    str,                      # assistant_text
    str,                      # phase
    Optional[List[str]],      # still_need
    Optional[Dict[str, Any]], # enrichment (weather_summary, booking_links, route_data)
]

# ---------------------------------------------------------------------------
# City-to-Country mapping for intelligent country inference
# ---------------------------------------------------------------------------

CITY_COUNTRY_MAP = {
    # Canada
    "toronto": "Canada",
    "vancouver": "Canada",
    "montreal": "Canada",
    "calgary": "Canada",
    "ottawa": "Canada",
    "winnipeg": "Canada",
    "edmonton": "Canada",
    "quebec": "Canada",
    
    # USA
    "new york": "USA",
    "los angeles": "USA",
    "chicago": "USA",
    "houston": "USA",
    "phoenix": "USA",
    "philadelphia": "USA",
    "san antonio": "USA",
    "san diego": "USA",
    "dallas": "USA",
    "san francisco": "USA",
    "boston": "USA",
    "seattle": "USA",
    "denver": "USA",
    "miami": "USA",
    "las vegas": "USA",
    "orlando": "USA",
    
    # Europe
    "paris": "France",
    "london": "UK",
    "berlin": "Germany",
    "rome": "Italy",
    "madrid": "Spain",
    "barcelona": "Spain",
    "amsterdam": "Netherlands",
    "vienna": "Austria",
    "prague": "Czech Republic",
    "bangkok": "Thailand",
    "zurich": "Switzerland",
    "lisbon": "Portugal",
    "dublin": "Ireland",
    "athens": "Greece",
    "istanbul": "Turkey",
    
    # Asia
    "tokyo": "Japan",
    "beijing": "China",
    "shanghai": "China",
    "hong kong": "China",
    "singapore": "Singapore",
    "bangkok": "Thailand",
    "seoul": "South Korea",
    "delhi": "India",
    "mumbai": "India",
    "bangkok": "Thailand",
    
    # Australia/Oceania
    "sydney": "Australia",
    "melbourne": "Australia",
    "brisbane": "Australia",
    "perth": "Australia",
    "auckland": "New Zealand",
    
    # South America
    "buenos aires": "Argentina",
    "rio de janeiro": "Brazil",
    "sao paulo": "Brazil",
    "santiago": "Chile",
    "lima": "Peru",
    "bogota": "Colombia",
}

# Ambiguous cities with multiple options
AMBIGUOUS_CITIES = {
    "springfield": ["USA (Illinois)", "USA (Massachusetts)", "USA (Missouri)"],
    "jackson": ["USA (Mississippi)", "USA (Wyoming)", "USA (Tennessee)"],
    "oxford": ["UK", "USA (Mississippi)"],
    "cambridge": ["UK", "USA (Massachusetts)"],
    "salem": ["USA (Oregon)", "USA (Massachusetts)", "USA (North Carolina)"],
}

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

INTAKE_SYSTEM_PROMPT = """\
You are a friendly, human-like travel assistant. Your job is to \
collect the traveller's trip details through a natural multi-turn conversation.

MANDATORY OUTPUT FORMAT:
Every response MUST end with this tracking line on a new line:
"Still need: <list>"

Where <list> is comma-separated missing REQUIRED fields from: city, country, travel dates, pace
Remove a field from the list ONLY when the user explicitly provides it.
Never include optional fields (interests, budget) unless user mentions them.
Write "Still need: none" when ready to generate itinerary.

Rules you MUST follow:
1. Your FIRST response must be a warm greeting and a short request for trip \
details (destination city/country, dates, pace).
2. After each user message, acknowledge what you understood in ONE natural \
sentence, then ask ONLY for the next missing piece.
3. NEVER mention internal mechanics — no "database", "AI", "Airflow", \
"pipeline", "extracted", "slots", "parameters", or "JSON".
4. Keep responses concise: 1-3 short paragraphs, conversational tone.
5. Do NOT repeat the same template sentence across turns.
6. COUNTRY INFERENCE: When user mentions a city, intelligently infer the country:
   - Common cities (Toronto, Paris, London, etc.) → You know the country, ask for confirmation
   - Example: If user says "Paris", say "Great! So Paris, France – I've got that." \
   (remove country from "still need")
   - Ambiguous cities (Springfield, Jackson, etc.) → Offer options to user
   - Example: If user says "Springfield", ask "Which Springfield? Springfield, Illinois, \
   Massachusetts, or Missouri?"
   - Once country is clear (either inferred or user confirms), remove "country" from still_need

Step A — Collect REQUIRED fields first (in any order):
- Destination city (which city to visit)
- Country (which country that city is in)
- Travel dates (start date + end date, OR start date + number of days)
- Pace (relaxed, moderate, or packed)

Step B — Collect OPTIONAL fields (mention naturally if user brings them up):
- Interests (e.g. museums, food, nature, sports, nightlife, culture, entertainment)
- Location preference (where to stay: downtown, waterfront, etc.)

Step C — MANDATORY: Once you have city, country, dates, and pace, you MUST ask BOTH booking questions:
1. FIRST ask: "Would you like help booking a flight ticket to [City]? If so, what city are you traveling from?"
2. THEN ask: "And would you like help finding an Airbnb or accommodation for your stay?"
Do NOT skip these questions. Do NOT assume. Always ask explicitly.

Step D — Only AFTER asking both booking questions, ask for final confirmation:
"Perfect! I have all the details. Should I go ahead and generate your [City] itinerary now?"

CRITICAL: You MUST complete Steps A, then C, then D in order.
Do NOT jump straight to generating or discussing the itinerary.
Do NOT skip the booking questions in Step C.

Do NOT ask about budget — it is not needed.
Do NOT generate the itinerary until the user explicitly confirms.

RESPONSE FORMAT EXAMPLES:

Example 1 - Initial greeting:
"Hey there! Welcome to the Trip Planner! I'd love to help you put together a great travel itinerary. To get started, could you tell me a bit about your trip? Things like where you're planning to visit (city and country), when you're traveling, what kinds of activities you enjoy, and whether you'd like a relaxed, moderate, or packed schedule?
Still need: city, country, travel dates, pace"

Example 2a - After user says "Paris from March 15-17" (known city, infer country):
"Great! Paris, France – perfect choice for a March getaway. So you're looking at a 3-day trip from March 15 to 17. What kind of pace are you thinking - relaxed, moderate, or packed with activities?
Still need: pace"

Example 2b - After user says "Springfield on April 1-3" (ambiguous city):
"Springfield – which one are you thinking of? Springfield, Illinois; Springfield, Massachusetts; or Springfield, Missouri? Once I know that, I can help you plan the perfect trip!
Still need: country, travel dates, pace"

Example 2c - After user says "Toronto from Feb 28 to March 3" (known city confirmed):
"You're planning a trip to Toronto, Canada from February 28 to March 3 – that's a 3-day adventure in a great Canadian city. What kind of pace are you thinking for your trip - relaxed, moderate, or packed with activities?
Still need: pace"

Example 3 - After user confirms pace "relaxed" (all required fields collected):
"Perfect! Now that I know you're heading to Toronto, Canada from February 28 to March 3 with a relaxed pace, I have a couple more quick questions. Would you like help booking a flight ticket to Toronto? If so, what city are you traveling from?
Still need: none"

Example 4 - After user answers booking questions OR says no:
"Great! I have everything I need. Should I go ahead and generate your Toronto itinerary now?
Still need: none"
"""

ITINERARY_SYSTEM_PROMPT_TEMPLATE = """\
You are a travel itinerary generator. ONLY use venues from the list below.

VENUE LIST — START
{venue_catalogue}
VENUE LIST — END

STRICT OUTPUT RULES:
1. Each day MUST have EXACTLY 2 meals: Lunch and Dinner \
(use food/restaurant venues from the list).
2. Activities per day (NON-MEAL time slots) based on pace:
   - relaxed pace: 2 activities (Morning + Afternoon)
   - moderate pace: 3 activities (Morning + Afternoon + Evening)
   - packed pace: 4 activities (Early Morning + Morning + Afternoon + Evening)
3. Every single line MUST include a Source citation: (Source: <venue_id>, <url>)
4. Exact format per day:

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
6. Do NOT add facts not in the venue record (prices, hours, events).
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

# Patterns that indicate the user is confirming itinerary generation
_AFFIRMATIVE_PATTERNS = re.compile(
    r"^\s*(yes\s*,?\s*please|yes|yeah|yep|yup|sure|go\s*ahead|please\s*do|"
    r"let'?s?\s*do\s*it|let'?s?\s*go|absolutely|ok|okay|sounds\s*good|"
    r"generate\s*it|generate|do\s*it|for\s*sure|definitely|of\s*course|"
    r"yes\s*,?\s*generate\s*it|please)"
    r"[.!]?\s*$",
    re.IGNORECASE,
)

# Phrase the assistant uses when all fields are collected
_CONFIRMATION_MARKER = "generate your itinerary"


class ConversationService:
    """Manages the conversational intake and grounded itinerary generation."""

    def __init__(
        self,
        orchestrator: Optional[ItineraryOrchestrator] = None,
    ) -> None:
        # Try Groq first, fallback to Gemini
        self.use_groq = False
        self.use_gemini = False

        try:
            from config.settings import settings
            if settings.GROQ_API_KEY:
                self.groq_client = GroqClient()
                self.use_groq = True
                logger.info("ConversationService: Using Groq as primary LLM")
        except Exception as e:
            logger.warning(f"ConversationService: Groq unavailable ({e}), trying Gemini")

        if not self.use_groq:
            try:
                self.gemini_client = GeminiClient()
                self.use_gemini = True
                logger.info("ConversationService: Using Gemini as LLM")
            except Exception as e:
                logger.error(f"ConversationService: No LLM available! Groq and Gemini both failed.")
                raise ValueError("No LLM available - both Groq and Gemini failed to initialize")

        try:
            self.venue_service = VenueService()
        except Exception:
            logger.warning("VenueService init failed — will use fallback venues")
            self.venue_service = None  # type: ignore[assignment]

        # Orchestrator for enriched itinerary generation (optional)
        self.orchestrator = orchestrator

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def turn(
        self,
        messages: List[Dict[str, str]],
        user_input: Optional[str],
    ) -> TurnResult:
        """
        Process one conversation turn.

        Args:
            messages: Full conversation history (system + user + assistant).
            user_input: The latest user message (None to trigger greeting).

        Returns:
            Tuple of (updated_messages, assistant_text, phase, still_need, enrichment).
            ``enrichment`` is a dict with weather_summary, booking_links, route_data
            (only populated in the itinerary phase; None otherwise).
        """
        # --- Phase: greeting (empty conversation) -------------------------
        if not messages or (not user_input and len(messages) == 0):
            return self._greeting()

        # --- Append user message ------------------------------------------
        if user_input:
            messages.append({"role": "user", "content": user_input})

        # --- Phase: itinerary generation (user confirmed) -----------------
        if self._user_is_confirming(messages, user_input):
            return await self._generate_grounded_itinerary(messages)

        # --- Phase: intake (continue collecting details) ------------------
        return await self._intake_turn(messages)

    # ------------------------------------------------------------------
    # Phase handlers
    # ------------------------------------------------------------------

    def _greeting(self) -> TurnResult:
        """Return a warm greeting without calling the LLM."""
        greeting = (
            "Hey there! Welcome to the Trip Planner! "
            "I'd love to help you put together a great travel itinerary. "
            "To get started, could you tell me a bit about your trip? "
            "Things like where you're planning to visit (city and country), "
            "when you're traveling, "
            "what kinds of activities you enjoy, and whether you'd like "
            "a relaxed, moderate, or packed schedule?"
        )
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
            {"role": "assistant", "content": greeting},
        ]
        return (
            messages,
            greeting,
            "greeting",
            ["city", "country", "travel dates", "pace"],
            None,  # no enrichment
        )

    async def _intake_turn(
        self, messages: List[Dict[str, str]],
    ) -> TurnResult:
        """Run one intake turn through Groq or Gemini."""
        # Ensure the system prompt is present
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": INTAKE_SYSTEM_PROMPT})

        loop = asyncio.get_running_loop()
        response_text: str = ""

        # Try Groq first
        if self.use_groq:
            try:
                response_text = await loop.run_in_executor(
                    None,
                    lambda: self.groq_client.chat_with_history(
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1024,
                    ),
                )
            except Exception as e:
                logger.warning(f"Groq failed in intake_turn, trying Gemini: {e}")
                if not hasattr(self, 'gemini_client'):
                    self.gemini_client = GeminiClient()
                self.use_gemini = True

        # Fallback to Gemini
        if not response_text and self.use_gemini:
            response_text = await loop.run_in_executor(
                None,
                lambda: self.gemini_client.chat_with_history(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1024,
                ),
            )

        if not response_text:
            raise Exception("No LLM response - both Groq and Gemini failed")

        # Bug C fix: parse "Still need:" before stripping it from user-visible text
        still_need = self._parse_still_need(response_text)
        
        # Fallback: If LLM didn't provide tracking, validate from conversation
        if still_need is None:
            logger.warning("LLM did not provide 'Still need:' tracking line, using fallback validation")
            still_need = self._validate_fields_from_conversation(messages)
            logger.info(f"Fallback validation result - Still need: {still_need}")
        else:
            logger.info(f"LLM tracking - Still need: {still_need}")
            
        # Strip any "Still need:" debug lines so they never reach the user
        clean_lines = [
            line for line in response_text.splitlines()
            if not line.strip().lower().startswith("still need:")
        ]
        response_text = "\n".join(clean_lines).strip()

        messages.append({"role": "assistant", "content": response_text})

        # Detect confirmation question
        phase = "intake"
        if _CONFIRMATION_MARKER.lower() in response_text.lower():
            phase = "confirmed"

        return messages, response_text, phase, still_need, None

    async def _generate_grounded_itinerary(
        self, messages: List[Dict[str, str]],
    ) -> TurnResult:
        """Fetch venues, build grounded prompt, and generate the itinerary.

        If an ``ItineraryOrchestrator`` is available, it handles weather,
        weather, booking, route enrichment in parallel with venue fetch.  Otherwise
        falls back to the original venues-only flow.
        """
        # ── Enriched path (orchestrator available) ────────────────────
        if self.orchestrator:
            try:
                # Ensure Gemini client is available for fallback
                gemini = getattr(self, "gemini_client", None)
                if not gemini and not self.use_groq:
                    gemini = GeminiClient()
                    self.gemini_client = gemini

                # Extract booking preferences from conversation history
                booking_type, source_location = self._extract_booking_info(messages)

                result = await self.orchestrator.generate_enriched_itinerary(
                    messages=messages,
                    llm_caller=None,  # not used; clients passed directly
                    use_groq=self.use_groq,
                    use_gemini=self.use_gemini or gemini is not None,
                    groq_client=getattr(self, "groq_client", None),
                    gemini_client=getattr(self, "gemini_client", None),
                    booking_type=booking_type,
                    source_location=source_location,
                )

                itinerary_text = result["itinerary_text"]
                messages.append({"role": "assistant", "content": itinerary_text})

                enrichment: Dict[str, Any] = {
                    "weather_summary": result.get("weather_summary"),
                    "booking_links": result.get("booking_links"),
                    "route_data": result.get("route_data"),
                }
                return messages, itinerary_text, "itinerary", None, enrichment

            except Exception as exc:
                logger.error(
                    "Orchestrator failed, falling back to basic itinerary: %s",
                    exc,
                    exc_info=True,
                )
                # Fall through to legacy path below

        # ── Legacy path (no orchestrator) ─────────────────────────────
        loop = asyncio.get_running_loop()
        venues: List[Dict[str, Any]] = []  # Bug B fix: initialize before conditional

        # Extract city from conversation for dynamic venue fetching
        city = None
        for msg in messages:
            if msg["role"] == "user":
                content = msg["content"].lower()
                # Simple extraction - look for common patterns
                import re
                city_match = re.search(r'(?:visit|visiting|trip to|going to)\s+([A-Z][a-zA-Z\s]+?)(?:\s|,|\.|\?|!|$)', msg["content"])
                if city_match:
                    city = city_match.group(1).strip()
                    break
        
        if not city:
            city = "Toronto"  # Default fallback
        
        if self.venue_service:
            venues = await loop.run_in_executor(
                None, 
                lambda: self.venue_service.get_all_venues_for_city(city, limit=50),
            )
        
        # Fallback to Toronto venues if query fails or returns empty
        if not venues:
            from services.venue_service import TORONTO_FALLBACK_VENUES
            venues = list(TORONTO_FALLBACK_VENUES)

        venue_catalogue = VenueService.format_venues_for_chat(venues)

        itinerary_system = ITINERARY_SYSTEM_PROMPT_TEMPLATE.format(
            venue_catalogue=venue_catalogue,
        )

        itinerary_messages: List[Dict[str, str]] = [
            {"role": "system", "content": itinerary_system},
        ]
        for m in messages:
            if m["role"] != "system":
                itinerary_messages.append(m)
        
        # Build dynamic message using extracted city
        city_ref = city if city and city != "Toronto" else "my"
        
        itinerary_messages.append(
            {
                "role": "user",
                "content": (
                    f"Please generate {city_ref} itinerary now based on "
                    "everything I told you. Use ONLY venues from the venue "
                    "list and include Source citations on every line."
                ),
            }
        )

        response_text: str = ""

        if self.use_groq:
            try:
                response_text = await loop.run_in_executor(
                    None,
                    lambda: self.groq_client.chat_with_history(
                        messages=itinerary_messages,
                        temperature=0.7,
                        max_tokens=4096,
                    ),
                )
            except Exception as e:
                logger.warning(f"Groq failed in generate_grounded_itinerary, trying Gemini: {e}")
                if not hasattr(self, "gemini_client"):
                    self.gemini_client = GeminiClient()
                self.use_gemini = True

        if not response_text and self.use_gemini:
            response_text = await loop.run_in_executor(
                None,
                lambda: self.gemini_client.chat_with_history(
                    messages=itinerary_messages,
                    temperature=0.7,
                    max_tokens=4096,
                ),
            )

        if not response_text:
            raise Exception("No LLM response - both Groq and Gemini failed")

        messages.append({"role": "assistant", "content": response_text})

        return messages, response_text, "itinerary", None, None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_booking_info(
        messages: List[Dict[str, str]],
    ) -> Tuple[str, Optional[str]]:
        """Scan conversation history to detect flight/Airbnb requests and source city."""
        user_texts = " ".join(m["content"] for m in messages if m.get("role") == "user")

        # Detect affirmative response to flight question
        wants_flight = bool(
            re.search(r"\b(yes|yeah|sure|yep|ok|okay|please|fly|flight|flying)\b",
                      user_texts, re.IGNORECASE)
            and re.search(r"(flight|fly|flying from|departing from|ticket)",
                          user_texts, re.IGNORECASE)
        )

        # Detect affirmative response to Airbnb question
        wants_airbnb = bool(re.search(
            r"\b(yes|yeah|sure|yep|ok|okay|please)\b.{0,30}"
            r"(airbnb|stay|accommodation|place to stay|place)",
            user_texts, re.IGNORECASE,
        ))

        # Extract source location (departure city)
        source_match = re.search(
            r"(?:flying from|departing from|traveling from|i.?m from|from)\s+"
            r"([A-Z][a-zA-Z\s]+?)(?:\s*[,.\?!]|$)",
            user_texts,
        )
        source_location = source_match.group(1).strip() if source_match else None

        if wants_flight and wants_airbnb:
            booking_type = "both"
        elif wants_flight:
            booking_type = "transportation"
        elif wants_airbnb:
            booking_type = "accommodation"
        else:
            booking_type = "none"

        return booking_type, source_location

    @staticmethod
    def _user_is_confirming(
        messages: List[Dict[str, str]], user_input: Optional[str]
    ) -> bool:
        """Check if the user is saying 'yes' to the confirmation question."""
        if not user_input:
            return False

        # The user's input must match an affirmative pattern
        if not _AFFIRMATIVE_PATTERNS.match(user_input.strip()):
            return False

        # The previous assistant message must contain the confirmation marker
        for msg in reversed(messages):
            if msg["role"] == "assistant":
                return _CONFIRMATION_MARKER.lower() in msg["content"].lower()
            if msg["role"] == "user":
                # We just appended the user message; skip it
                continue

        return False

    @staticmethod
    def _parse_still_need(text: str) -> Optional[List[str]]:
        """Extract the ``Still need: ...`` line from the assistant response."""
        for line in reversed(text.strip().splitlines()):
            stripped = line.strip()
            if stripped.lower().startswith("still need:"):
                remainder = stripped.split(":", 1)[1].strip()
                if not remainder or remainder.lower() in ("none", "nothing", "n/a"):
                    return []
                return [item.strip() for item in remainder.split(",") if item.strip()]
        return None

    def _validate_fields_from_conversation(self, messages: List[Dict[str, str]]) -> List[str]:
        """
        Fallback validation: Check what fields are missing by parsing conversation.
        Returns list of missing required fields.
        """
        user_texts = " ".join(m["content"] for m in messages if m.get("role") == "user")
        combined = user_texts
        combined_lower = combined.lower()
        
        logger.debug(f"Validating conversation text: '{combined}'")
        
        missing = []
        
        # Check for city (any capitalized word that's likely a place name, or common cities)
        city_found = bool(
            re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b', combined) or  # Any capitalized word
            re.search(r'\b(visit|visiting|trip to|going to|traveling to)\s+\w+', combined_lower)  # Travel context
        )
        logger.debug(f"City found: {city_found}")
        if not city_found:
            missing.append("city")
        
        # Check for country (look for country names or assume if city is clear)
        country_found = bool(re.search(
            r'\b(canada|france|uk|usa|japan|germany|italy|spain|england|united states|united kingdom|china|australia|mexico|brazil)\b',
            combined_lower
        ))
        
        # Infer country from city if possible
        country_inferred = False
        for city_name, country_name in CITY_COUNTRY_MAP.items():
            if re.search(rf'\b{city_name}\b', combined_lower):
                country_inferred = True
                logger.debug(f"Country inferred from city '{city_name}': {country_name}")
                break
        
        logger.debug(f"Country found: {country_found}, Country inferred: {country_inferred}")
        if not country_found and not country_inferred:
            missing.append("country")
        
        # Check for dates (various formats and date ranges)
        date_patterns = [
            # Date ranges with "from X to Y"
            r'from\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}\s+to\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}',
            # Month name + day
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+\d{1,2}',
            # ISO date format
            r'\d{4}-\d{2}-\d{2}',
            # Slash format
            r'\b\d{1,2}/\d{1,2}',
            # Date ranges "X to Y", "X - Y"
            r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s*\d{1,2}\s*(?:to|-|through|until)\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s*\d{1,2}',
            # Number + days/nights
            r'\d+\s*(?:day|night)s?',
        ]
        
        date_found = any(re.search(pattern, combined_lower) for pattern in date_patterns)
        logger.debug(f"Date found: {date_found} in text: '{combined_lower}'")
        if not date_found:
            missing.append("travel dates")
        
        # Check for pace
        pace_found = bool(re.search(
            r'\b(relaxed|relax|moderate|packed|fast|slow|chill|busy|easy|laid.?back|normal|balanced|intense|hectic)\b',
            combined_lower
        ))
        logger.debug(f"Pace found: {pace_found}")
        if not pace_found:
            missing.append("pace")
        
        logger.debug(f"Validation complete - Missing fields: {missing}")
        return missing

    @staticmethod
    def infer_country_from_city(city_name: str) -> Optional[str]:
        """
        Try to infer the country from a city name.
        
        Returns:
            - Country name if found uniquely
            - None if not found or ambiguous
        """
        city_lower = city_name.lower().strip()
        
        # Check if it's in our unique mapping
        if city_lower in CITY_COUNTRY_MAP:
            return CITY_COUNTRY_MAP[city_lower]
        
        return None

    @staticmethod
    def get_ambiguous_country_options(city_name: str) -> Optional[List[str]]:
        """
        Get country options if the city is ambiguous.
        
        Returns:
            - List of country options if ambiguous
            - None if not ambiguous or not found
        """
        city_lower = city_name.lower().strip()
        
        if city_lower in AMBIGUOUS_CITIES:
            return AMBIGUOUS_CITIES[city_lower]
        
        return None
