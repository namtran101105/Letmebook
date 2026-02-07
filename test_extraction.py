"""
Test script for the NLP extraction service.
Run this to test the chatbot's ability to extract preferences from user input.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.nlp_extraction_service import NLPExtractionService
from config.settings import settings


def test_extraction():
    """Test the NLP extraction with sample inputs."""

    # Validate settings first
    try:
        settings.validate()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nPlease:")
        print("1. Copy backend/.env.example to backend/.env")
        print("2. Add your Gemini API key to backend/.env")
        return

    # Create service instance
    service = NLPExtractionService()

    # Test cases
    test_messages = [
        "I want to visit Kingston next weekend with my family of 4. We love history and food tours. Budget is around $500-800.",
        "Planning a solo trip to Kingston from July 15-20. I'm vegetarian and interested in museums and hiking. Prefer staying in an Airbnb.",
        "Weekend getaway for 2, interested in waterfront activities and local breweries. Don't want anything too touristy.",
    ]

    print("=" * 80)
    print("NLP EXTRACTION SERVICE TEST")
    print("=" * 80)

    for i, message in enumerate(test_messages, 1):
        print(f"\n{'─' * 80}")
        print(f"TEST {i}")
        print(f"{'─' * 80}")
        print(f"\n📝 User Input:")
        print(f"   {message}")

        try:
            # Extract preferences
            print("\n⏳ Extracting preferences...")
            preferences = service.extract_preferences(message)

            # Validate
            validation = service.validate_preferences(preferences)

            print(f"\n✅ Extracted Preferences:")
            print(f"   Trip ID: {preferences.trip_id}")
            print(f"   Dates: {preferences.start_date} to {preferences.end_date}")
            print(f"   Duration: {preferences.duration_days} days" if preferences.duration_days else "   Duration: Not specified")
            print(f"   Budget: ${preferences.budget_min}-${preferences.budget_max} {preferences.budget_currency}" if preferences.budget_min else "   Budget: Not specified")
            print(f"   Interests: {', '.join(preferences.interests)}" if preferences.interests else "   Interests: None specified")
            print(f"   Group: {preferences.group_size} people" if preferences.group_size else "   Group: Not specified")
            print(f"   Traveling with: {preferences.traveling_with}" if preferences.traveling_with else "")
            print(f"   Dietary: {', '.join(preferences.dietary_restrictions)}" if preferences.dietary_restrictions else "")
            print(f"   Must see: {', '.join(preferences.must_see)}" if preferences.must_see else "")
            print(f"   Accommodation: {preferences.accommodation_type}" if preferences.accommodation_type else "")
            print(f"   Confidence: {preferences.confidence_score:.2%}" if preferences.confidence_score else "")

            print(f"\n📊 Validation:")
            print(f"   Valid: {'✅ Yes' if validation['valid'] else '❌ No'}")
            print(f"   Completeness: {validation['completeness_score']:.1%}")
            if validation['warnings']:
                print(f"   Warnings: {', '.join(validation['warnings'])}")
            if validation['issues']:
                print(f"   Issues: {', '.join(validation['issues'])}")

            print(f"\n📄 Full JSON:")
            print("   " + preferences.to_json().replace("\n", "\n   "))

        except Exception as e:
            print(f"\n❌ Error: {str(e)}")

    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print("=" * 80)


def test_refinement():
    """Test preference refinement with additional input."""
    print("\n\n" + "=" * 80)
    print("REFINEMENT TEST")
    print("=" * 80)

    service = NLPExtractionService()

    # Initial message
    initial = "I want to visit Kingston next month for 3 days"
    print(f"\n📝 Initial Input: {initial}")

    try:
        preferences = service.extract_preferences(initial)
        print(f"\n✅ Initial Extraction:")
        print(f"   Duration: {preferences.duration_days} days")
        print(f"   Interests: {preferences.interests}")

        # Additional information
        additional = "Actually, I'm really interested in visiting Fort Henry and trying local wines. Budget is $600."
        print(f"\n📝 Additional Input: {additional}")

        refined = service.refine_preferences(preferences, additional)
        print(f"\n✅ Refined Extraction:")
        print(f"   Duration: {refined.duration_days} days")
        print(f"   Interests: {', '.join(refined.interests)}" if refined.interests else "   Interests: None")
        print(f"   Must see: {', '.join(refined.must_see)}" if refined.must_see else "   Must see: None")
        print(f"   Budget: ${refined.budget_min}-${refined.budget_max}" if refined.budget_min else "   Budget: Not specified")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    test_extraction()
    # Uncomment to test refinement:
    # test_refinement()
