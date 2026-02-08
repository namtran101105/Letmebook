"""
Conversation service — manages the full multi-turn chat lifecycle for the
Toronto-only itinerary MVP.

Phases:
    1. greeting   — first response; warm welcome + ask for trip details
    2. intake     — collect dates, budget, interests, pace over multiple turns
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
    Optional[Dict[str, Any]], # enrichment (weather_summary, budget_summary, route_data)
]

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

INTAKE_SYSTEM_PROMPT = """\
You are a friendly, human-like Toronto travel assistant. Your job is to \
collect the traveller's trip details through a natural multi-turn conversation.

City is ALWAYS Toronto, Canada — do not ask which city.

Rules you MUST follow:
1. Your FIRST response must be a warm greeting and a short request for trip \
details (dates, budget, interests, pace).
2. After each user message, acknowledge what you understood in ONE natural \
sentence, then ask ONLY for the next missing piece.
3. NEVER mention internal mechanics — no "database", "AI", "Airflow", \
"pipeline", "extracted", "slots", "parameters", or "JSON".
4. Keep responses concise: 1-3 short paragraphs, conversational tone.
5. Do NOT repeat the same template sentence across turns.

Required fields (collect ALL before confirming):
- Travel dates (start date + end date, OR start date + number of days)
- Budget (total amount in CAD)
- Interests (at least one: e.g. museums, food, nature, sports, nightlife, \
culture, entertainment)
- Pace (relaxed, moderate, or packed)

After EVERY response, add this line at the very end on its own line:
Still need: <comma-separated list of fields still missing>

If ALL four fields are collected, instead of "Still need:" write EXACTLY:
"Awesome — I have everything I need! Want me to generate your Toronto \
itinerary now?"

Do NOT generate the itinerary until the user explicitly confirms.\
"""

ITINERARY_SYSTEM_PROMPT_TEMPLATE = """\
You are a Toronto travel itinerary generator. You MUST ONLY use venues from \
the venue list below. This is a hard constraint — do NOT invent venues.

VENUE LIST — START
{venue_catalogue}
VENUE LIST — END

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
_CONFIRMATION_MARKER = "generate your Toronto itinerary"


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
            ``enrichment`` is a dict with weather_summary, budget_summary, route_data
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
            "Hey there! Welcome to the Toronto Trip Planner! "
            "I'd love to help you put together a great Toronto itinerary. "
            "To get started, could you tell me a bit about your trip? "
            "Things like when you're planning to visit, your budget, "
            "what kinds of activities you enjoy, and whether you'd like "
            "a relaxed, moderate, or packed schedule?\n\n"
            "Still need: travel dates, budget, interests, pace"
        )
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
            {"role": "assistant", "content": greeting},
        ]
        return (
            messages,
            greeting,
            "greeting",
            ["travel dates", "budget", "interests", "pace"],
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

        messages.append({"role": "assistant", "content": response_text})

        # Parse "Still need:" line
        still_need = self._parse_still_need(response_text)

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
        budget, route enrichment in parallel with venue fetch.  Otherwise
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

                result = await self.orchestrator.generate_enriched_itinerary(
                    messages=messages,
                    llm_caller=None,  # not used; clients passed directly
                    use_groq=self.use_groq,
                    use_gemini=self.use_gemini or gemini is not None,
                    groq_client=getattr(self, "groq_client", None),
                    gemini_client=getattr(self, "gemini_client", None),
                )

                itinerary_text = result["itinerary_text"]
                messages.append({"role": "assistant", "content": itinerary_text})

                enrichment: Dict[str, Any] = {
                    "weather_summary": result.get("weather_summary"),
                    "budget_summary": result.get("budget_summary"),
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
        if self.venue_service:
            venues = await loop.run_in_executor(
                None, self.venue_service.get_toronto_venues,
            )
        else:
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
