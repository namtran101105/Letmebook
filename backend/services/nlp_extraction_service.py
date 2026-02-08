"""
NLP service for extracting structured trip preferences from natural language input.
Uses Groq API (primary) or Gemini API (fallback) to parse user messages and extract travel details.
Supports multi-turn conversation to collect all required fields including flight/Airbnb needs.
"""
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from clients.gemini_client import GeminiClient
from clients.groq_client import GroqClient
from models.trip_preferences import TripPreferences
from config.settings import settings


class NLPExtractionService:
    """Service for extracting trip preferences from natural language."""

    def __init__(self, use_groq: bool = True):
        """
        Initialize the extraction service with Groq (primary) or Gemini (fallback) client.

        Args:
            use_groq: If True, use Groq API. If False, use Gemini API.
        """
        self.use_groq = use_groq
        self.use_gemini = False

        try:
            # Try Groq first (primary)
            if use_groq and settings.GROQ_API_KEY:
                self.groq_client = GroqClient()
                self.gemini_client = None
                self.use_groq = True
                self.use_gemini = False
                print("✅ Using Groq API (Primary)")
            # Fallback to Gemini if Groq not available
            elif settings.GEMINI_KEY:
                self.gemini_client = GeminiClient()
                self.groq_client = None
                self.use_groq = False
                self.use_gemini = True
                print("✅ Using Gemini API (Fallback)")
            else:
                raise ValueError("No API keys configured. Set GROQ_API_KEY or GEMINI_KEY in .env")
        except Exception as e:
            # If Groq fails, try Gemini as fallback
            if not self.use_gemini:
                try:
                    print(f"⚠️  Groq initialization failed, trying Gemini fallback: {e}")
                    self.gemini_client = GeminiClient()
                    self.groq_client = None
                    self.use_groq = False
                    self.use_gemini = True
                    print("✅ Using Gemini API (Fallback)")
                except Exception as gemini_error:
                    raise ValueError(f"Both Groq and Gemini initialization failed. Groq: {e}, Gemini: {gemini_error}")

        self.system_instruction = self._build_system_instruction()

    def _build_system_instruction(self) -> str:
        """Build the system instruction for the AI model."""
        return """You are a friendly travel planning assistant specializing in extracting structured information from natural language.

        Your task is to analyze user messages about their trip and extract relevant details into a structured JSON format.

        Extract the following information when available:
        - City and country (if mentioned)
        - Travel dates (start_date, end_date in YYYY-MM-DD format, or duration_days)
        - Interests: Classify into EXACTLY these 5 categories (use only these names):
          * "Food and Beverage" — restaurants, cafes, food tours, breweries, wine, street food, dining, etc.
          * "Entertainment" — shopping, casino, spa, bar, pub, arcade, nightlife, cinema, concerts, zoo, aquarium, etc.
          * "Culture and History" — museums, libraries, churches, castles, fortresses, old quarters, monuments, art galleries, sightseeing, etc.
          * "Sport" — soccer, basketball, NFL, NBA, stadium, golf, tennis, skiing, cycling, swimming, etc.
          * "Natural Place" — national parks, beaches, lakes, fishing, diving, trekking, hiking, mountains, gardens, waterfalls, etc.
          Only include categories the user actually mentions or implies. Return as an array of category names.
        - Pace of travel (relaxed, moderate, packed). Synonyms: relax/chill/slow/leisurely/easy → "relaxed", balanced/normal/steady → "moderate", fast/rush/busy/intense/active → "packed"
        - Location preference for drop-off or stay (e.g., "downtown", "near nature", "historic district", or "flexible")
        - Booking needs:
          * needs_flight: true if user says yes to needing a flight ticket, false if they say no, null if not yet asked or answered
          * needs_airbnb: true if user says yes to needing Airbnb/accommodation, false if they say no, null if not yet asked or answered
          * source_location: Where user is traveling from (only if needs_flight is true and they mention their departure city)

        Rules:
        1. Only extract information explicitly mentioned or strongly implied
        2. Use null for missing information - do not guess or make assumptions
        3. For dates:
           - Specific dates: Convert to YYYY-MM-DD format (e.g., "March 15 2026" → "2026-03-15")
           - Month only: Use format "YYYY-MM" or "Month YYYY" (e.g., "November" → "November 2026", "July 2026" → "2026-07")
           - Season: Store as "season YYYY" (e.g., "winter" → "winter 2026", "summer 2024" → "summer 2024")
           - Flexible: If user says "flexible", "anytime", "not sure yet" → set start_date to "flexible"
           - Duration: Extract number of days/weeks (e.g., "5 days" → duration_days: 5, "2 weeks" → duration_days: 14)
        4. For interests, classify into the 5 categories listed above. Return only the matching category names, not the raw activities
        5. For needs_flight: detect from user saying "yes" to flight question, "I need a flight", "flying from X", etc.
        6. For needs_airbnb: detect from user saying "yes" to Airbnb question, "I need accommodation", "book an Airbnb", etc.
        7. For source_location, extract city/airport when user mentions: "from [city]", "coming from [city]", "flying from [city]", "I live in [city]"
        8. Be conservative - better to leave something null than to guess incorrectly
        9. Return valid JSON only, no additional text"""

    def _build_extraction_prompt(self, user_input: str) -> str:
        """
        Build the prompt for extracting preferences.

        Args:
            user_input: The user's natural language message

        Returns:
            Formatted prompt string
        """
        json_schema = {
            "city": "string or null",
            "country": "string or null",
            "start_date": "string or null (YYYY-MM-DD)",
            "end_date": "string or null (YYYY-MM-DD)",
            "duration_days": "integer or null",
            "interests": "array of strings — ONLY use these exact category names: 'Food and Beverage', 'Entertainment', 'Culture and History', 'Sport', 'Natural Place'. Can be empty array.",
            "pace": "string or null (relaxed/moderate/packed). Map synonyms: relax/chill/slow/easy → relaxed, fast/rush/busy/intense → packed",
            "location_preference": "string or null (e.g., downtown, near nature, historic district, or 'flexible')",
            "needs_flight": "boolean or null — true if user says yes to needing a flight, false if no, null if not mentioned yet",
            "needs_airbnb": "boolean or null — true if user says yes to needing Airbnb, false if no, null if not mentioned yet",
            "source_location": "string or null (city user is flying from, only if needs_flight is true)"
        }

        prompt = f"""Extract travel preferences from this user message:

        User message: "{user_input}"

        Return a JSON object with the following structure:
        {json.dumps(json_schema, indent=2)}

        Remember:
        - Only include information that is mentioned or strongly implied
        - Use null for missing information
        - Return arrays as empty [] if no items are mentioned
        - Location: If user says "anywhere", "no preference", "flexible" → set location_preference to "flexible"
        - Dates:
          * Specific dates → "YYYY-MM-DD" format
          * Month only → "YYYY-MM" or "Month YYYY" format
          * Season → "season YYYY" format (e.g., "winter 2026")
          * Flexible → "flexible"
          * Duration → number of days in duration_days field
        - If start_date + end_date are provided, duration_days will be auto-calculated (you can leave it null)
        - If start_date + duration_days are provided, end_date will be auto-calculated (you can leave it null)
        - needs_flight: only set to true/false if user explicitly responds to this question. Otherwise null.
        - needs_airbnb: only set to true/false if user explicitly responds to this question. Otherwise null.
        - Return ONLY valid JSON, no additional text or explanation

        JSON response:"""

        return prompt

    async def extract_preferences(self, user_input: str) -> TripPreferences:
        """
        Extract structured trip preferences from user's natural language input.

        Args:
            user_input: The user's message describing their trip

        Returns:
            TripPreferences object with extracted information
        """
        if not user_input or not user_input.strip():
            raise ValueError("User input cannot be empty")

        # Build the extraction prompt
        prompt = self._build_extraction_prompt(user_input)

        try:
            if self.use_groq and self.groq_client:
                # Call Groq API (sync) — run in thread pool to avoid blocking
                loop = asyncio.get_running_loop()
                extracted_data = await loop.run_in_executor(
                    None,
                    lambda: self.groq_client.generate_json(
                        prompt=prompt,
                        system_instruction=self.system_instruction,
                        temperature=settings.GROQ_TEMPERATURE,
                        max_tokens=settings.GROQ_MAX_TOKENS,
                    ),
                )

            elif self.use_gemini and self.gemini_client:
                # Call Gemini API (native async — no asyncio.run wrapper needed)
                extracted_text = await self.gemini_client.generate_content(
                    prompt=prompt,
                    system_instruction=self.system_instruction,
                    temperature=settings.GEMINI_EXTRACTION_TEMPERATURE,
                    max_tokens=settings.GEMINI_EXTRACTION_MAX_TOKENS,
                )

                # Parse JSON from response
                extracted_text = extracted_text.strip()
                if extracted_text.startswith("```json"):
                    extracted_text = extracted_text.split("```json")[1].split("```")[0].strip()
                elif extracted_text.startswith("```"):
                    extracted_text = extracted_text.split("```")[1].split("```")[0].strip()

                extracted_data = json.loads(extracted_text)
            else:
                raise ValueError("No LLM client available")

            # Create TripPreferences object
            preferences = TripPreferences.from_dict(extracted_data)

            # Auto-calculate missing date fields
            preferences = self._calculate_date_fields(preferences)

            return preferences

        except Exception as e:
            raise Exception(f"Failed to extract preferences: {str(e)}")

    def _get_next_question_phase(self, preferences: TripPreferences) -> Optional[str]:
        """
        Determine the next piece of information needed in the conversation.

        Returns the phase name, or None if all questions have been asked.
        """
        # Phase 1: Required fields
        if not preferences.city:
            return "city"
        if not preferences.country:
            return "country"
        if not preferences.start_date and not preferences.end_date and not preferences.duration_days:
            return "dates"
        if not preferences.pace:
            return "pace"

        # Phase 2: Booking questions (asked after required fields are complete)
        if preferences.needs_flight is None:
            return "flight"
        if preferences.needs_flight and not preferences.source_location:
            return "source_location"
        if preferences.needs_airbnb is None:
            return "airbnb"

        # All done
        return None

    async def generate_conversational_response(
        self,
        user_input: str,
        preferences: TripPreferences,
        validation: Dict[str, Any],
        is_refinement: bool = False
    ) -> tuple[str, bool]:
        """
        Generate a natural conversational response based on extracted preferences.

        Args:
            user_input: Original user message
            preferences: Extracted TripPreferences object
            validation: Validation results from validate_preferences()
            is_refinement: Whether this is a refinement (True) or initial extraction (False)

        Returns:
            Tuple of (bot_response_string, all_questions_asked)
        """
        # Determine the next question needed
        next_phase = self._get_next_question_phase(preferences)
        all_questions_asked = next_phase is None

        # Build context summary of what's been extracted
        extracted_info = []
        if preferences.city:
            extracted_info.append(f"City: {preferences.city}")
        if preferences.country:
            extracted_info.append(f"Country: {preferences.country}")
        if preferences.start_date and preferences.end_date:
            extracted_info.append(f"Dates: {preferences.start_date} to {preferences.end_date}")
        elif preferences.start_date:
            extracted_info.append(f"Start date: {preferences.start_date}")
        elif preferences.end_date:
            extracted_info.append(f"End date: {preferences.end_date}")
        elif preferences.duration_days:
            extracted_info.append(f"Duration: {preferences.duration_days} days")
        if preferences.interests and len(preferences.interests) > 0:
            extracted_info.append(f"Interests: {', '.join(preferences.interests)}")
        if preferences.pace:
            extracted_info.append(f"Pace: {preferences.pace}")
        if preferences.location_preference:
            extracted_info.append(f"Location preference: {preferences.location_preference}")
        if preferences.needs_flight is not None:
            extracted_info.append(f"Needs flight: {'Yes' if preferences.needs_flight else 'No'}")
        if preferences.needs_flight and preferences.source_location:
            extracted_info.append(f"Flying from: {preferences.source_location}")
        if preferences.needs_airbnb is not None:
            extracted_info.append(f"Needs Airbnb: {'Yes' if preferences.needs_airbnb else 'No'}")

        extracted_summary = "\n".join(extracted_info) if extracted_info else "No specific details extracted yet"

        # Map next phase to question description
        phase_to_question = {
            "city": "which city they'd like to visit",
            "country": "which country that city is in",
            "dates": "their travel dates (start date, end date, or how many days)",
            "pace": "their preferred travel pace: relaxed, moderate, or packed",
            "flight": "if they're coming from far away and whether they need a flight ticket booked",
            "source_location": "which city they'll be flying from",
            "airbnb": "if they need to book an Airbnb for their stay",
        }

        # Debug logging
        print(f"\n=== Conversational Response Debug ===")
        print(f"User input: {user_input}")
        print(f"Next phase: {next_phase}")
        print(f"All questions asked: {all_questions_asked}")
        print(f"Extracted summary:\n{extracted_summary}")
        print(f"=====================================\n")

        if all_questions_asked:
            # All info collected — ask for confirmation before generating itinerary
            system_instruction = """You are a warm and friendly travel assistant. All trip details have been collected.
Your job is to:
1. Briefly confirm the key trip details in 1-2 sentences (destination, dates, pace, and any booking needs)
2. Ask if they're ready to generate their personalized itinerary
Be concise, warm, and encouraging. Do NOT ask for more details."""

            booking_summary = []
            if preferences.needs_flight:
                booking_summary.append(f"flight from {preferences.source_location}")
            if preferences.needs_airbnb:
                booking_summary.append("Airbnb accommodation")
            booking_str = f", including {' and '.join(booking_summary)}" if booking_summary else ""

            prompt = f"""The user just said: "{user_input}"

All trip details are now complete:
{extracted_summary}

Booking arrangements{booking_str}.

Generate a warm confirmation (1-2 sentences) summarizing the key trip details and asking if they're ready to generate their itinerary.

Response:"""
        else:
            # Still collecting info — ask for the next required field
            next_question_desc = phase_to_question.get(next_phase, next_phase)

            system_instruction = """You are a warm, friendly travel assistant having a natural conversation.
Guidelines:
- Acknowledge what the user just shared (be specific and positive)
- Ask for the NEXT missing piece of information
- Keep it brief: 1-2 sentences max
- Be conversational, not robotic
- Never re-ask for info already provided
- For the flight question: be casual, e.g. "Are you traveling from far away? Would you like me to help find a flight?"
- For the Airbnb question: be casual, e.g. "Would you like me to find an Airbnb for your stay?"
- Budget is never asked about — it's not needed"""

            prompt = f"""User just said: "{user_input}"

What I know so far:
{extracted_summary if extracted_summary != "No specific details extracted yet" else "Nothing yet — this is the first message"}

Next thing to ask about: {next_question_desc}

Write a brief, friendly response (1-2 sentences) that acknowledges their input and asks for: {next_question_desc}

Response:"""

        try:
            # Generate conversational response using available LLM
            if self.use_groq and self.groq_client:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.groq_client.generate_content(
                        prompt=prompt,
                        system_instruction=system_instruction,
                        temperature=0.7,
                        max_tokens=300,
                    ),
                )
            elif self.use_gemini and self.gemini_client:
                response = await self.gemini_client.generate_content(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_tokens=300,
                )
            else:
                raise ValueError("No LLM client available")

            print(f"Generated response: {response.strip()}")
            return response.strip(), all_questions_asked

        except Exception as e:
            print(f"Warning: Failed to generate conversational response: {e}")
            import traceback
            traceback.print_exc()
            fallback = "Got it! " + (
                "I have all the info I need. Ready to generate your itinerary?"
                if all_questions_asked
                else f"Could you tell me your {next_question_desc}?"
            )
            return fallback, all_questions_asked

    async def refine_preferences(
        self,
        existing_preferences: TripPreferences,
        additional_input: str,
        last_question: Optional[str] = None
    ) -> TripPreferences:
        """
        Refine existing preferences with additional user input.

        Args:
            existing_preferences: Previously extracted preferences
            additional_input: New user input to incorporate
            last_question: The conversation phase that was last asked (for context)

        Returns:
            Updated TripPreferences object
        """
        # Add context about what was last asked so the AI can interpret "yes/no" answers correctly
        context_hints = {
            "flight": "The assistant just asked if the user needs a flight ticket. 'yes'/'sure'/'yeah' means needs_flight=true, 'no'/'nope'/'don't need one' means needs_flight=false.",
            "source_location": "The assistant just asked where the user will be flying from. Extract the city/location as source_location.",
            "airbnb": "The assistant just asked if the user needs Airbnb accommodation. 'yes'/'sure'/'yeah' means needs_airbnb=true, 'no'/'nope'/'don't need it' means needs_airbnb=false.",
        }
        context_note = ""
        if last_question and last_question in context_hints:
            context_note = f"\nCONVERSATION CONTEXT: {context_hints[last_question]}\n"

        prompt = f"""You have previously extracted these preferences from a user:

{existing_preferences.to_json()}

The user has now provided additional information:
"{additional_input}"
{context_note}
CRITICAL INSTRUCTIONS:
1. PRESERVE ALL EXISTING VALUES that are not explicitly updated by the new information
2. If the user provides ONLY a country, keep the existing city value - do NOT set city to null
3. If the user provides ONLY a city, keep the existing country value - do NOT set country to null
4. If the user says "anywhere", "no preference", "flexible", "anywhere is fine" for location → set location_preference to "flexible"
5. Only update fields that are explicitly mentioned or clearly implied in the new input
6. NEVER remove or null out existing values unless the new information directly contradicts them
7. For needs_flight/needs_airbnb: interpret "yes", "yeah", "sure", "please" as true; "no", "nope", "don't need" as false
8. For source_location: only set if needs_flight is true and user mentions where they're flying from

Examples:
- Existing: {{"city": "Kingston", "country": null}}, New: "Canada" → Result: {{"city": "Kingston", "country": "Canada"}}
- Existing: {{"city": null, "country": "France"}}, New: "Paris" → Result: {{"city": "Paris", "country": "France"}}
- Existing: {{"needs_flight": null}}, New: "yes please" (last_question=flight) → Result: {{"needs_flight": true}}
- Existing: {{"needs_flight": true, "source_location": null}}, New: "Montreal" → Result: {{"source_location": "Montreal"}}

Return the complete updated JSON object with the same structure:"""

        try:
            if self.use_groq and self.groq_client:
                loop = asyncio.get_running_loop()
                updated_data = await loop.run_in_executor(
                    None,
                    lambda: self.groq_client.generate_json(
                        prompt=prompt,
                        system_instruction=self.system_instruction,
                        temperature=settings.GROQ_TEMPERATURE,
                        max_tokens=settings.GROQ_MAX_TOKENS,
                    ),
                )
            elif self.use_gemini and self.gemini_client:
                extracted_text = await self.gemini_client.generate_content(
                    prompt=prompt,
                    system_instruction=self.system_instruction,
                    temperature=settings.GEMINI_EXTRACTION_TEMPERATURE,
                    max_tokens=settings.GEMINI_EXTRACTION_MAX_TOKENS,
                )

                extracted_text = extracted_text.strip()
                if extracted_text.startswith("```json"):
                    extracted_text = extracted_text.split("```json")[1].split("```")[0].strip()
                elif extracted_text.startswith("```"):
                    extracted_text = extracted_text.split("```")[1].split("```")[0].strip()

                updated_data = json.loads(extracted_text)
            else:
                raise ValueError("No LLM client available")

            updated_preferences = TripPreferences.from_dict(updated_data)

            # Auto-calculate missing date fields
            updated_preferences = self._calculate_date_fields(updated_preferences)

            return updated_preferences

        except Exception as e:
            raise Exception(f"Failed to refine preferences: {str(e)}")

    def _calculate_date_fields(self, preferences: TripPreferences) -> TripPreferences:
        """
        Auto-calculate missing date fields based on provided information.
        """
        from datetime import datetime, timedelta

        try:
            # Rule 1: If start_date and end_date provided → calculate duration_days
            if preferences.start_date and preferences.end_date and not preferences.duration_days:
                if len(preferences.start_date) == 10 and len(preferences.end_date) == 10:
                    try:
                        start = datetime.strptime(preferences.start_date, "%Y-%m-%d")
                        end = datetime.strptime(preferences.end_date, "%Y-%m-%d")
                        duration = (end - start).days + 1
                        if duration > 0:
                            preferences.duration_days = duration
                    except ValueError:
                        pass

            # Rule 2: If start_date + duration_days provided → calculate end_date
            elif preferences.start_date and preferences.duration_days and not preferences.end_date:
                if len(preferences.start_date) == 10:
                    try:
                        start = datetime.strptime(preferences.start_date, "%Y-%m-%d")
                        end = start + timedelta(days=preferences.duration_days - 1)
                        preferences.end_date = end.strftime("%Y-%m-%d")
                    except ValueError:
                        pass

            # Rule 3: If end_date + duration_days provided → calculate start_date
            elif preferences.end_date and preferences.duration_days and not preferences.start_date:
                if len(preferences.end_date) == 10:
                    try:
                        end = datetime.strptime(preferences.end_date, "%Y-%m-%d")
                        start = end - timedelta(days=preferences.duration_days - 1)
                        preferences.start_date = start.strftime("%Y-%m-%d")
                    except ValueError:
                        pass

        except Exception as e:
            print(f"Warning: Date calculation failed: {e}")

        return preferences

    def validate_preferences(self, preferences: TripPreferences) -> Dict[str, Any]:
        """
        Validate extracted preferences and return any warnings or issues.
        """
        issues = []
        warnings = []

        # Check for date consistency
        if preferences.start_date and preferences.end_date:
            if preferences.start_date > preferences.end_date:
                issues.append("Start date is after end date")

        has_dates = bool(preferences.start_date or preferences.end_date or preferences.duration_days)
        if not has_dates:
            warnings.append("No date information provided")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "completeness_score": self._calculate_completeness(preferences)
        }

    def _calculate_completeness(self, preferences: TripPreferences) -> float:
        """
        Calculate how complete the preferences are (0.0 to 1.0).
        Counts: city, country, dates, pace, needs_flight answered, source_location (if needed), needs_airbnb answered.
        """
        score = 0

        if preferences.city:
            score += 1
        if preferences.country:
            score += 1
        if preferences.start_date or preferences.end_date or preferences.duration_days:
            score += 1
        if preferences.pace:
            score += 1
        if preferences.needs_flight is not None:
            score += 1
        if preferences.needs_airbnb is not None:
            score += 1

        # Total depends on whether flight is needed (source_location adds one more)
        total = 6
        if preferences.needs_flight:
            total = 7
            if preferences.source_location:
                score += 1

        return min(score / total, 1.0)

    def save_preferences_to_file(
        self,
        preferences: TripPreferences,
        output_dir: str = "data/trip_requests"
    ) -> Optional[str]:
        """
        Save complete trip preferences to a JSON file.
        """
        try:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            full_output_dir = os.path.join(backend_dir, output_dir)
            os.makedirs(full_output_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            city_name = preferences.city or "unknown_city"
            city_name = "".join(c for c in city_name if c.isalnum() or c in (' ', '-', '_')).strip()
            city_name = city_name.replace(' ', '_').lower()

            filename = f"trip_{city_name}_{timestamp}.json"
            filepath = os.path.join(full_output_dir, filename)

            data = preferences.to_dict()
            data['_metadata'] = {
                'created_at': datetime.now().isoformat(),
                'file_version': '2.0'
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✅ Saved trip preferences to: {filepath}")
            return filepath

        except Exception as e:
            print(f"❌ Failed to save preferences to file: {e}")
            import traceback
            traceback.print_exc()
            return None
