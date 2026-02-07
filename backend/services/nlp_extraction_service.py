"""
NLP service for extracting structured trip preferences from natural language input.
Uses Groq API to parse user messages and extract travel details.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from clients.groq_client import GroqClient
from models.trip_preferences import TripPreferences
from config.settings import settings


class NLPExtractionService:
    """Service for extracting trip preferences from natural language."""

    def __init__(self):
        """Initialize the extraction service with Groq client."""
        self.groq_client = GroqClient()
        self.system_instruction = self._build_system_instruction()

    def _build_system_instruction(self) -> str:
        """Build the system instruction for the AI model."""
        return """You are a travel planning assistant specializing in extracting structured information from natural language.

        Your task is to analyze user messages about their trip and extract relevant details into a structured JSON format.

        Extract the following information when available:
        - City and country (if mentioned)
        - Travel dates (start_date, end_date in YYYY-MM-DD format, or duration_days)
        - Budget (single value in CAD)
        - Interests: Classify into EXACTLY these 5 categories (use only these names):
          * "Food and Beverage" — restaurants, cafes, food tours, breweries, wine, street food, dining, etc.
          * "Entertainment" — shopping, casino, spa, bar, pub, arcade, nightlife, cinema, concerts, zoo, aquarium, etc.
          * "Culture and History" — museums, libraries, churches, castles, fortresses, old quarters, monuments, art galleries, sightseeing, etc.
          * "Sport" — soccer, basketball, NFL, NBA, stadium, golf, tennis, skiing, cycling, swimming, etc.
          * "Natural Place" — national parks, beaches, lakes, fishing, diving, trekking, hiking, mountains, gardens, waterfalls, etc.
          Only include categories the user actually mentions or implies. Return as an array of category names.
        - Pace of travel (relaxed, moderate, packed). Synonyms: relax/chill/slow/leisurely/easy → "relaxed", balanced/normal/steady → "moderate", fast/rush/busy/intense/active → "packed"
        - Location preference for drop-off or stay (e.g., "downtown", "near nature", "historic district")

        Rules:
        1. Only extract information explicitly mentioned or strongly implied
        2. Use null for missing information - do not guess or make assumptions
        3. For dates:
           - Specific dates: Convert to YYYY-MM-DD format (e.g., "March 15 2026" → "2026-03-15")
           - Month only: Use format "YYYY-MM" or "Month YYYY" (e.g., "November" → "November 2026", "July 2026" → "2026-07")
           - Season: Store as "season YYYY" (e.g., "winter" → "winter 2026", "summer 2024" → "summer 2024")
           - Flexible: If user says "flexible", "anytime", "not sure yet" → set start_date to "flexible"
           - Duration: Extract number of days/weeks (e.g., "5 days" → duration_days: 5, "2 weeks" → duration_days: 14)
        4. For budget, extract a single value (if a range is given, use the midpoint or maximum)
        5. For interests, classify into the 5 categories listed above. Return only the matching category names, not the raw activities
        6. Be conservative - better to leave something null than to guess incorrectly
        7. Return valid JSON only, no additional text"""

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
            "budget": "number or null",
            "budget_currency": "string (default: CAD)",
            "interests": "array of strings — ONLY use these exact category names: 'Food and Beverage', 'Entertainment', 'Culture and History', 'Sport', 'Natural Place'",
            "pace": "string or null (relaxed/moderate/packed). Map synonyms: relax/chill/slow/easy → relaxed, fast/rush/busy/intense → packed",
            "location_preference": "string or null (e.g., downtown, near nature, historic district)"
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
        - Return ONLY valid JSON, no additional text or explanation

        JSON response:"""

        return prompt

    def extract_preferences(self, user_input: str) -> TripPreferences:
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
            # Call Groq API to extract preferences as JSON
            extracted_data = self.groq_client.generate_json(
                prompt=prompt,
                system_instruction=self.system_instruction,
                temperature=settings.EXTRACTION_TEMPERATURE,
                max_tokens=settings.EXTRACTION_MAX_TOKENS
            )

            # Create TripPreferences object
            preferences = TripPreferences(**extracted_data)

            # Auto-calculate missing date fields
            preferences = self._calculate_date_fields(preferences)

            return preferences

        except Exception as e:
            raise Exception(f"Failed to extract preferences: {str(e)}")

    def generate_conversational_response(
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
            Natural language bot response string
        """
        # Build context-aware prompt
        completeness_pct = int(validation['completeness_score'] * 100)

        # Check if all preferences are complete (100%)
        is_complete = validation['completeness_score'] >= 1.0

        # Prepare extracted info summary
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

        if preferences.budget:
            budget_str = f"${preferences.budget} {preferences.budget_currency}"
            if preferences.duration_days and preferences.duration_days > 0:
                daily = preferences.budget / preferences.duration_days
                budget_str += f" (~${daily:.0f}/day)"
            elif preferences.start_date and preferences.end_date:
                # Calculate days between dates
                from datetime import datetime
                try:
                    start = datetime.strptime(preferences.start_date, "%Y-%m-%d")
                    end = datetime.strptime(preferences.end_date, "%Y-%m-%d")
                    days = (end - start).days + 1
                    if days > 0:
                        daily = preferences.budget / days
                        budget_str += f" (~${daily:.0f}/day)"
                except:
                    pass
            extracted_info.append(f"Budget: {budget_str}")

        if preferences.interests and len(preferences.interests) > 0:
            extracted_info.append(f"Interests: {', '.join(preferences.interests)}")

        if preferences.pace:
            extracted_info.append(f"Pace: {preferences.pace}")

        if preferences.location_preference:
            extracted_info.append(f"Location preference: {preferences.location_preference}")

        extracted_summary = "\n".join(extracted_info) if extracted_info else "No specific details extracted yet"

        # Check for specific missing fields in priority order:
        # 1. City, 2. Country, 3. Location preference, 4. Dates, 5. Interests & Pace, 6. Budget
        missing_fields = []

        # Priority 1: City
        if not preferences.city:
            missing_fields.append("city")

        # Priority 2: Country
        if not preferences.country:
            missing_fields.append("country")

        # Priority 3: Location preference
        if not preferences.location_preference:
            missing_fields.append("location preference")

        # Priority 4: Dates (start/end date + duration)
        if not preferences.start_date and not preferences.end_date and not preferences.duration_days:
            missing_fields.append("dates (start date, end date, or duration)")

        # Priority 5: Interests and Pace
        if not preferences.interests or len(preferences.interests) == 0:
            missing_fields.append("interests")
        if not preferences.pace:
            missing_fields.append("pace")

        # Priority 6: Budget
        if not preferences.budget:
            missing_fields.append("budget")

        missing_fields_str = ", ".join(missing_fields) if missing_fields else "None"

        # Check if all questions have been asked (no missing fields)
        all_questions_asked = len(missing_fields) == 0

        # Debug logging
        print(f"\n=== Conversational Response Debug ===")
        print(f"User input: {user_input}")
        print(f"Completeness: {completeness_pct}%")
        print(f"Is complete: {is_complete}")
        print(f"All questions asked: {all_questions_asked} (will save JSON: {'YES' if all_questions_asked else 'NO'})")
        print(f"Extracted summary:\n{extracted_summary}")
        print(f"Missing fields: {missing_fields_str}")
        print(f"=====================================\n")

        # Build prompt based on completeness
        if is_complete:
            # All preferences are filled - ask for simple confirmation
            system_instruction = """You are a friendly travel planning assistant. Your role is to:
1. Acknowledge that you have all the information needed
2. Briefly confirm the key trip details (destination, dates, budget, interests, pace)
3. Ask ONLY for confirmation - a simple yes/no question
4. Be warm, encouraging, and very concise (1-2 sentences max)
5. Use a friendly tone

Important:
- Do NOT ask for more information - all preferences are complete
- Do NOT offer to add more details or make changes
- Simple confirmation only: "Shall I proceed?", "Does this work for you?", "Ready to confirm?"
- Be positive and direct"""

            context_type = "refinement/update" if is_refinement else "initial message"

            prompt = f"""The user sent this {context_type}: "{user_input}"

I have now collected ALL required trip preferences:
{extracted_summary}

Validation results:
- Completeness: 100% (ALL FIELDS COMPLETE)
- Valid: {validation['valid']}
- Warnings: {', '.join(validation['warnings']) if validation['warnings'] else 'None'}
- Issues: {', '.join(validation['issues']) if validation['issues'] else 'None'}

Generate a conversational response that:
1. {"Acknowledges the update" if is_refinement else "Acknowledges completion"}
2. Briefly confirms the key details in ONE sentence (destination, dates, main interest)
3. Asks ONLY for confirmation - a simple question expecting yes/no
4. Is warm and encouraging (1-2 sentences MAXIMUM)
5. Does NOT ask if they want to add more or make changes
6. Does NOT list every single detail - keep it brief

Example: "Perfect! I have your Kingston trip from Feb 15-17 with museum visits and fast pace. Shall I proceed with planning your itinerary?"

Response:"""
        else:
            # Preferences incomplete - continue asking for missing info
            system_instruction = """You are a friendly travel planning assistant collecting trip information.

RULES:
1. Acknowledge what the user just shared
2. Ask for the NEXT missing field from the priority list
3. Keep responses SHORT (2 sentences max)
4. NEVER re-ask for fields already provided
5. Be warm and encouraging"""

            context_type = "refinement/update" if is_refinement else "initial message"

            # Determine the next field(s) to ask for based on priority
            next_field_to_ask = None
            if "city" in missing_fields_str:
                next_field_to_ask = "city (which city do you want to visit?)"
            elif "country" in missing_fields_str:
                next_field_to_ask = "country (which country is that city in?)"
            elif "location preference" in missing_fields_str:
                next_field_to_ask = "location preference (optional - where in the city will you stay? e.g., downtown, near airport, or say 'flexible' if you don't have a preference)"
            elif "dates" in missing_fields_str:
                next_field_to_ask = "dates (when will you travel? Please provide start date, end date, or duration)"
            elif "interests" in missing_fields_str and "pace" in missing_fields_str:
                next_field_to_ask = "interests and pace (what are you interested in? Choose from: Food & Beverage, Entertainment, Culture & History, Sport, or Natural Places. And what pace: relaxed, moderate, or packed?)"
            elif "interests" in missing_fields_str:
                next_field_to_ask = "interests (what are you interested in? Choose from: Food & Beverage, Entertainment, Culture & History, Sport, or Natural Places — or just describe what you enjoy!)"
            elif "pace" in missing_fields_str:
                next_field_to_ask = "pace (what pace do you prefer for your trip: relaxed, moderate, or packed?)"
            elif "budget" in missing_fields_str:
                next_field_to_ask = "budget (what's your total or daily budget for this trip?)"

            prompt = f"""User just said: "{user_input}"

What I extracted from their message:
{extracted_summary if extracted_summary != "No specific details extracted yet" else "Nothing new yet"}

Missing information: {missing_fields_str}

TASK: Write a brief, friendly response (2 sentences max) that:
1. Acknowledges what they just shared
2. Asks for: {next_field_to_ask}

Example format: "Got it, [acknowledge their input]! [Ask for next field?]"

Response:"""

        try:
            # Generate conversational response using Groq API
            response = self.groq_client.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.7,  # Higher temp for more natural variety
                max_tokens=300  # Keep responses concise
            )

            print(f"Generated response: {response.strip()}")
            print(f"All questions asked: {all_questions_asked}")
            return response.strip(), all_questions_asked

        except Exception as e:
            # Fallback to static message if generation fails
            print(f"Warning: Failed to generate conversational response: {e}")
            import traceback
            traceback.print_exc()
            fallback_message = "✅ I've updated your preferences! Check the panel on the right for details." if is_refinement else "✅ I've extracted your preferences! Check the panel on the right for details."
            return fallback_message, all_questions_asked

    def refine_preferences(
        self,
        existing_preferences: TripPreferences,
        additional_input: str
    ) -> TripPreferences:
        """
        Refine existing preferences with additional user input.

        Args:
            existing_preferences: Previously extracted preferences
            additional_input: New user input to incorporate

        Returns:
            Updated TripPreferences object
        """
        # Build a prompt that includes existing preferences
        prompt = f"""You have previously extracted these preferences from a user:

{existing_preferences.to_json()}

The user has now provided additional information:
"{additional_input}"

CRITICAL INSTRUCTIONS:
1. PRESERVE ALL EXISTING VALUES that are not explicitly updated by the new information
2. If the user provides ONLY a country, keep the existing city value - do NOT set city to null
3. If the user provides ONLY a city, keep the existing country value - do NOT set country to null
4. If the user says "anywhere", "no preference", "flexible", "anywhere is fine", "anywhere is okay" for location → set location_preference to "flexible"
5. Only update fields that are explicitly mentioned or clearly implied in the new input
6. NEVER remove or null out existing values unless the new information directly contradicts them

Examples:
- Existing: {{"city": "Kingston", "country": null}}, New: "Canada" → Result: {{"city": "Kingston", "country": "Canada"}}
- Existing: {{"city": null, "country": "France"}}, New: "Paris" → Result: {{"city": "Paris", "country": "France"}}
- Existing: {{"city": "Tokyo", "country": "Japan"}}, New: "anywhere is okay" → Result: {{"location_preference": "flexible"}}, keep city and country

Return the complete updated JSON object with the same structure:"""

        try:
            updated_data = self.groq_client.generate_json(
                prompt=prompt,
                system_instruction=self.system_instruction,
                temperature=settings.EXTRACTION_TEMPERATURE,
                max_tokens=settings.EXTRACTION_MAX_TOKENS
            )

            updated_preferences = TripPreferences.from_dict(updated_data)

            # Auto-calculate missing date fields
            updated_preferences = self._calculate_date_fields(updated_preferences)

            return updated_preferences

        except Exception as e:
            raise Exception(f"Failed to refine preferences: {str(e)}")

    def _calculate_date_fields(self, preferences: TripPreferences) -> TripPreferences:
        """
        Auto-calculate missing date fields based on provided information.

        Rules:
        - If start_date + end_date provided → calculate duration_days
        - If start_date + duration_days provided → calculate end_date
        - If end_date + duration_days provided → calculate start_date

        Args:
            preferences: TripPreferences object with some date fields filled

        Returns:
            Updated TripPreferences with calculated date fields
        """
        from datetime import datetime, timedelta

        try:
            # Rule 1: If start_date and end_date provided → calculate duration_days
            if preferences.start_date and preferences.end_date and not preferences.duration_days:
                # Check if dates are in YYYY-MM-DD format (specific dates, not month/season)
                if len(preferences.start_date) == 10 and len(preferences.end_date) == 10:
                    try:
                        start = datetime.strptime(preferences.start_date, "%Y-%m-%d")
                        end = datetime.strptime(preferences.end_date, "%Y-%m-%d")
                        duration = (end - start).days + 1  # +1 to include both start and end days
                        if duration > 0:
                            preferences.duration_days = duration
                    except ValueError:
                        pass  # Not valid date format, skip calculation

            # Rule 2: If start_date + duration_days provided → calculate end_date
            elif preferences.start_date and preferences.duration_days and not preferences.end_date:
                if len(preferences.start_date) == 10:  # Specific date format
                    try:
                        start = datetime.strptime(preferences.start_date, "%Y-%m-%d")
                        end = start + timedelta(days=preferences.duration_days - 1)  # -1 because duration includes start day
                        preferences.end_date = end.strftime("%Y-%m-%d")
                    except ValueError:
                        pass

            # Rule 3: If end_date + duration_days provided → calculate start_date
            elif preferences.end_date and preferences.duration_days and not preferences.start_date:
                if len(preferences.end_date) == 10:  # Specific date format
                    try:
                        end = datetime.strptime(preferences.end_date, "%Y-%m-%d")
                        start = end - timedelta(days=preferences.duration_days - 1)  # -1 because duration includes end day
                        preferences.start_date = start.strftime("%Y-%m-%d")
                    except ValueError:
                        pass

        except Exception as e:
            # If any calculation fails, just return preferences as-is
            print(f"Warning: Date calculation failed: {e}")

        return preferences

    def validate_preferences(self, preferences: TripPreferences) -> Dict[str, Any]:
        """
        Validate extracted preferences and return any warnings or issues.

        Args:
            preferences: The preferences to validate

        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []

        # Check for date consistency
        if preferences.start_date and preferences.end_date:
            if preferences.start_date > preferences.end_date:
                issues.append("Start date is after end date")

        # Check if we have minimal required information
        has_dates = bool(preferences.start_date or preferences.end_date or preferences.duration_days)
        has_preferences = bool(preferences.interests and len(preferences.interests) > 0)

        if not has_dates:
            warnings.append("No date information provided")
        if not has_preferences:
            warnings.append("No specific interests mentioned")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "completeness_score": self._calculate_completeness(preferences)
        }

    def _calculate_completeness(self, preferences: TripPreferences) -> float:
        """
        Calculate how complete the preferences are (0.0 to 1.0).

        Args:
            preferences: The preferences to evaluate

        Returns:
            Completeness score between 0.0 and 1.0
        """
        # Required fields (location_preference is optional - useful for layovers/transits but not always needed)
        required_fields = [
            'city', 'country',
            'start_date', 'end_date', 'duration_days',
            'budget',
            'interests', 'pace'
        ]

        filled_count = 0
        for field in required_fields:
            value = getattr(preferences, field, None)
            if value is not None and value != [] and value != '':
                filled_count += 1

        return filled_count / len(required_fields)

    def save_preferences_to_file(
        self,
        preferences: TripPreferences,
        output_dir: str = "data/trip_requests"
    ) -> Optional[str]:
        """
        Save complete trip preferences to a JSON file.

        Args:
            preferences: The TripPreferences object to save
            output_dir: Directory to save the file (relative to backend/)

        Returns:
            Absolute path to the saved file, or None if save failed
        """
        try:
            # Create output directory if it doesn't exist
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            full_output_dir = os.path.join(backend_dir, output_dir)
            os.makedirs(full_output_dir, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            city_name = preferences.city or "unknown_city"
            # Sanitize city name for filename
            city_name = "".join(c for c in city_name if c.isalnum() or c in (' ', '-', '_')).strip()
            city_name = city_name.replace(' ', '_').lower()

            filename = f"trip_{city_name}_{timestamp}.json"
            filepath = os.path.join(full_output_dir, filename)

            # Convert preferences to dict and add metadata
            data = preferences.to_dict()
            data['_metadata'] = {
                'created_at': datetime.now().isoformat(),
                'file_version': '1.0'
            }

            # Write to file with pretty formatting
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✅ Saved trip preferences to: {filepath}")
            return filepath

        except Exception as e:
            print(f"❌ Failed to save preferences to file: {e}")
            import traceback
            traceback.print_exc()
            return None
